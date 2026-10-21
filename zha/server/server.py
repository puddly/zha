"""Server exposing a ZHA `Gateway` to clients."""

from __future__ import annotations

from collections.abc import Callable
import inspect
import logging
from types import TracebackType
from typing import TYPE_CHECKING, Any, Self

from zigpy.types.named import EUI64

from zha.application.const import (
    ZHA_DEVICE_ENTITY_ADDED_EVENT,
    ZHA_DEVICE_ENTITY_REMOVED_EVENT,
    ZHA_GW_MSG_DEVICE_FULL_INIT,
    ZHA_GW_MSG_DEVICE_REMOVED,
    ZHA_GW_MSG_GROUP_ADDED,
    ZHA_GW_MSG_GROUP_MEMBER_ADDED,
    ZHA_GW_MSG_GROUP_MEMBER_REMOVED,
    ZHA_GW_MSG_GROUP_REMOVED,
)
from zha.application.platforms import (
    BaseEntity,
    BaseIdentifiers,
    GroupEntityIdentifiers,
    PlatformEntityIdentifiers,
)
from zha.common.commands import entity_commands
from zha.common.messages import (
    START_LISTENING,
    CommandMessage,
    DeviceTarget,
    EventMessage,
    GatewayTarget,
    GroupTarget,
    InitialState,
    Target,
)

if TYPE_CHECKING:
    from zha.application.gateway import Gateway
    from zha.zigbee.device import BaseDevice
    from zha.zigbee.group import Group, GroupMemberReference

_LOGGER = logging.getLogger(__name__)

DEVICE_COMMANDS: frozenset[str] = frozenset(
    {
        "device_info",
        "extended_device_info",
        "get_diagnostics_json",
        "write_zigbee_attribute",
        "issue_cluster_command",
        "async_add_to_group",
        "async_remove_from_group",
        "async_add_endpoint_to_group",
        "async_remove_endpoint_from_group",
        "async_bind_to_group",
        "async_unbind_from_group",
    }
)

GROUP_COMMANDS: frozenset[str] = frozenset(
    {
        "async_add_members",
        "async_remove_members",
    }
)


class Server:
    """Forwards gateway, device, group, and entity events and dispatches commands."""

    def __init__(self, gateway: Gateway) -> None:
        """Initialize the server."""
        self.gateway = gateway
        self._listeners: list[Callable[[EventMessage], None]] = []
        self._gateway_unsub: Callable[[], None] | None = None
        self._device_unsubs: dict[EUI64, tuple[BaseDevice, Callable[[], None]]] = {}
        self._entity_unsubs: dict[
            BaseIdentifiers, tuple[BaseEntity, Callable[[], None]]
        ] = {}

        # Gateway commands return server objects, so each one is adapted here
        self._gateway_commands: dict[str, Callable[..., Any]] = {
            START_LISTENING: self.get_initial_state,
            "async_create_zigpy_group": self._create_group,
            "async_remove_zigpy_group": gateway.async_remove_zigpy_group,
            "async_reinterview_device": gateway.async_reinterview_device,
            "async_remove_device": gateway.async_remove_device,
        }

    def start(self) -> None:
        """Subscribe to everything the gateway currently knows about."""
        self._gateway_unsub = self.gateway.on_all_events(self._handle_gateway_event)
        for device in self.gateway.devices.values():
            self._sync_device(device)
        for group in self.gateway.groups.values():
            self._sync_group(group)

    def stop(self) -> None:
        """Unsubscribe from the gateway."""
        if self._gateway_unsub is not None:
            self._gateway_unsub()
            self._gateway_unsub = None
        for _device, unsub in self._device_unsubs.values():
            unsub()
        self._device_unsubs.clear()
        for _entity, unsub in self._entity_unsubs.values():
            unsub()
        self._entity_unsubs.clear()

    async def __aenter__(self) -> Self:
        """Start forwarding events."""
        self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Stop forwarding events."""
        self.stop()

    def subscribe(self, callback: Callable[[EventMessage], None]) -> Callable[[], None]:
        """Register a listener for every event the server forwards."""
        self._listeners.append(callback)

        def unsubscribe() -> None:
            self._listeners.remove(callback)

        return unsubscribe

    def get_initial_state(self) -> InitialState:
        """Snapshot the gateway."""
        assert self.gateway.coordinator_zha_device is not None
        return InitialState(
            coordinator_ieee=self.gateway.coordinator_zha_device.ieee,
            devices=[
                device.extended_device_info for device in self.gateway.devices.values()
            ],
            groups=[group.state for group in self.gateway.groups.values()],
        )

    async def handle_command(self, message: CommandMessage) -> Any:
        """Dispatch a command to its target and return the result."""
        result = self._call(message)
        if inspect.isawaitable(result):
            return await result
        return result

    def handle_command_no_wait(self, message: CommandMessage) -> None:
        """Dispatch a command without reporting its result."""
        result = self._call(message)
        if inspect.iscoroutine(result):
            self.gateway.async_create_task(
                result, name=f"server-{message.command}", eager_start=True
            )

    async def _create_group(
        self,
        name: str,
        members: list[GroupMemberReference] | None,
        group_id: int | None = None,
    ) -> int | None:
        group = await self.gateway.async_create_zigpy_group(name, members, group_id)
        return None if group is None else group.group_id

    def _call(self, message: CommandMessage) -> Any:
        target = message.target

        if isinstance(target, GatewayTarget):
            return self._gateway_commands[message.command](**message.args)

        if isinstance(target, DeviceTarget):
            device = self.gateway.devices[target.ieee]
            return self._invoke(device, DEVICE_COMMANDS, message)

        if isinstance(target, GroupTarget):
            group = self.gateway.groups[target.group_id]
            return self._invoke(group, GROUP_COMMANDS, message)

        entity = self._resolve_entity(target)
        return self._invoke(entity, entity_commands(type(entity)), message)

    def _resolve_entity(self, target: BaseIdentifiers) -> BaseEntity:
        if isinstance(target, PlatformEntityIdentifiers):
            device = self.gateway.devices[target.device_ieee]
            return device.get_platform_entity(target.platform, target.unique_id)  # type: ignore[arg-type]

        assert isinstance(target, GroupEntityIdentifiers)
        group = self.gateway.groups[target.group_id]
        return group.group_entities[target.unique_id]

    def _invoke(
        self, obj: Any, allowed: frozenset[str], message: CommandMessage
    ) -> Any:
        if message.command not in allowed:
            raise ValueError(f"Command {message.command!r} is not accepted by {obj!r}")

        attr = getattr(obj, message.command)

        # Properties such as `device_info` are exposed as argument-less commands
        if not callable(attr):
            return attr

        return attr(**message.args)

    def _publish(self, source: Target, event: Any) -> None:
        message = EventMessage(source=source, event=event)
        for listener in list(self._listeners):
            listener(message)

    def _handle_gateway_event(self, event: Any) -> None:
        # Keep server-side subscriptions in step with the gateway before clients
        # see the event, so that entity events for the new objects are forwarded
        if event.event == ZHA_GW_MSG_DEVICE_FULL_INIT:
            self._sync_device(self.gateway.devices[event.device_info.ieee])
        elif event.event == ZHA_GW_MSG_DEVICE_REMOVED:
            if event.device_info.ieee in self._device_unsubs:
                self._drop_device(event.device_info.ieee)
        elif event.event in (
            ZHA_GW_MSG_GROUP_ADDED,
            ZHA_GW_MSG_GROUP_MEMBER_ADDED,
            ZHA_GW_MSG_GROUP_MEMBER_REMOVED,
        ):
            self._sync_group(self.gateway.groups[event.group_info.group_id])
        elif event.event == ZHA_GW_MSG_GROUP_REMOVED:
            self._drop_group_entities(event.group_info.group_id)

        self._publish(GatewayTarget(), event)

    def _sync_device(self, device: BaseDevice) -> None:
        existing = self._device_unsubs.get(device.ieee)

        # A re-interview can replace the device object under the same IEEE
        if existing is not None and existing[0] is not device:
            self._drop_device(device.ieee)
            existing = None

        if existing is None:

            def handle_device_event(event: Any) -> None:
                self._handle_device_event(device, event)

            self._device_unsubs[device.ieee] = (
                device,
                device.on_all_events(handle_device_event),
            )

        self._sync_entities(
            {
                identifiers: entity
                for identifiers, entity in self._entity_unsubs.items()
                if isinstance(identifiers, PlatformEntityIdentifiers)
                and identifiers.device_ieee == device.ieee
            },
            device.platform_entities.values(),
        )

    def _drop_device(self, ieee: EUI64) -> None:
        _device, unsub = self._device_unsubs.pop(ieee)
        unsub()
        for identifiers in list(self._entity_unsubs):
            if (
                isinstance(identifiers, PlatformEntityIdentifiers)
                and identifiers.device_ieee == ieee
            ):
                self._unsubscribe_entity(identifiers)

    def _handle_device_event(self, device: BaseDevice, event: Any) -> None:
        if event.event == ZHA_DEVICE_ENTITY_ADDED_EVENT:
            self._subscribe_entity(
                device.get_platform_entity(event.platform, event.unique_id)
            )
        elif event.event == ZHA_DEVICE_ENTITY_REMOVED_EVENT:
            for identifiers in list(self._entity_unsubs):
                if (
                    isinstance(identifiers, PlatformEntityIdentifiers)
                    and identifiers.device_ieee == device.ieee
                    and identifiers.unique_id == event.unique_id
                    and identifiers.platform == event.platform
                ):
                    self._unsubscribe_entity(identifiers)

        self._publish(DeviceTarget(ieee=device.ieee), event)

    def _sync_group(self, group: Group) -> None:
        self._sync_entities(
            {
                identifiers: entity
                for identifiers, entity in self._entity_unsubs.items()
                if isinstance(identifiers, GroupEntityIdentifiers)
                and identifiers.group_id == group.group_id
            },
            group.group_entities.values(),
        )

    def _drop_group_entities(self, group_id: int) -> None:
        for identifiers in list(self._entity_unsubs):
            if (
                isinstance(identifiers, GroupEntityIdentifiers)
                and identifiers.group_id == group_id
            ):
                self._unsubscribe_entity(identifiers)

    def _sync_entities(
        self,
        subscribed: dict[BaseIdentifiers, tuple[BaseEntity, Callable[[], None]]],
        current: Any,
    ) -> None:
        """Drop subscriptions to entities that no longer exist, add the rest."""
        current_by_id = {entity.identifiers: entity for entity in current}
        for identifiers, (entity, _unsub) in subscribed.items():
            if current_by_id.get(identifiers) is not entity:
                self._unsubscribe_entity(identifiers)
        for entity in current_by_id.values():
            self._subscribe_entity(entity)

    def _subscribe_entity(self, entity: BaseEntity) -> None:
        identifiers = entity.identifiers
        if identifiers in self._entity_unsubs:
            return

        def handle_entity_event(event: Any) -> None:
            self._publish(identifiers, event)

        self._entity_unsubs[identifiers] = (
            entity,
            entity.on_all_events(handle_entity_event),
        )

    def _unsubscribe_entity(self, identifiers: BaseIdentifiers) -> None:
        _entity, unsub = self._entity_unsubs.pop(identifiers)
        unsub()


class LocalTransport:
    """In-process transport: the client calls the server directly."""

    def __init__(self, server: Server) -> None:
        """Initialize the transport."""
        self.server = server

    async def send_command(self, message: CommandMessage) -> Any:
        """Dispatch the command on the server and return its result."""
        return await self.server.handle_command(message)

    def send_command_no_wait(self, message: CommandMessage) -> None:
        """Dispatch the command on the server without reporting its result."""
        self.server.handle_command_no_wait(message)

    def subscribe(self, callback: Callable[[EventMessage], None]) -> Callable[[], None]:
        """Forward server events to the callback."""
        return self.server.subscribe(callback)
