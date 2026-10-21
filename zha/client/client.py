"""ZHA client."""

from __future__ import annotations

from collections.abc import Callable
import logging
from types import TracebackType
from typing import TYPE_CHECKING, Any, Self
import uuid

from zha.application import Platform
from zha.application.platforms import GroupEntityIdentifiers, PlatformEntityIdentifiers
from zha.client.gateway import Gateway
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
from zha.server.server import LocalTransport

if TYPE_CHECKING:
    from zha.common.transport import Transport
    from zha.server.server import Server

_LOGGER = logging.getLogger(__name__)


class Client:
    """Connects to a ZHA server and maintains a model of its gateway."""

    def __init__(self, transport: Transport) -> None:
        """Initialize the client."""
        self._transport = transport
        self._unsubscribe: Callable[[], None] | None = None
        self.gateway: Gateway | None = None

    @property
    def server(self) -> Server | None:
        """Return the in-process server, when the transport is local."""
        if isinstance(self._transport, LocalTransport):
            return self._transport.server
        return None

    @property
    def connected(self) -> bool:
        """Return whether the client is listening."""
        return self._unsubscribe is not None

    async def connect(self) -> Gateway:
        """Fetch the initial state and start listening for events."""
        initial: InitialState = await self.send_command(
            GatewayTarget(), START_LISTENING
        )
        self.gateway = Gateway(self, initial)
        self._unsubscribe = self._transport.subscribe(self._handle_event)
        return self.gateway

    async def disconnect(self) -> None:
        """Stop listening."""
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        self.gateway = None

    async def __aenter__(self) -> Self:
        """Connect to the server."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Disconnect from the server."""
        await self.disconnect()

    async def send_command(self, target: Target, command: str, **args: Any) -> Any:
        """Send a command and wait for its result."""
        return await self._transport.send_command(
            CommandMessage(
                message_id=uuid.uuid4().hex, target=target, command=command, args=args
            )
        )

    def send_command_no_wait(self, target: Target, command: str, **args: Any) -> None:
        """Send a command without waiting for its result."""
        self._transport.send_command_no_wait(
            CommandMessage(
                message_id=uuid.uuid4().hex, target=target, command=command, args=args
            )
        )

    def _handle_event(self, message: EventMessage) -> None:
        assert self.gateway is not None
        source = message.source

        if isinstance(source, GatewayTarget):
            self.gateway.receive_event(message.event)
        elif isinstance(source, DeviceTarget):
            self.gateway.devices[source.ieee].receive_event(message.event)
        elif isinstance(source, GroupTarget):
            _LOGGER.debug("Ignoring group event %s", message.event)
        elif isinstance(source, PlatformEntityIdentifiers):
            device = self.gateway.devices[source.device_ieee]
            device.platform_entities[
                (Platform(source.platform), source.unique_id)
            ].receive_event(message.event)
        elif isinstance(source, GroupEntityIdentifiers):
            group = self.gateway.groups[source.group_id]
            group.group_entities[source.unique_id].receive_event(message.event)
        else:
            raise TypeError(f"Unknown event source: {source!r}")
