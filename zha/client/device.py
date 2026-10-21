"""Client-side device model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from zigpy.types.named import EUI64, NWK

from zha.application import Platform
from zha.application.const import ATTR_COMMAND, POWER_MAINS_POWERED
from zha.client.entity import Entity, Remote, remote
from zha.client.platforms import create_entity
from zha.common.messages import DeviceTarget
from zha.event import EventBase
from zha.zigbee.device import (
    DeviceAvailabilityChangedEvent,
    DeviceEntityAddedEvent,
    DeviceEntityRemovedEvent,
    DeviceFirmwareInfoUpdatedEvent,
    DeviceInfo,
    ExtendedDeviceInfo,
    ZigbeeDevice,
)

if TYPE_CHECKING:
    from zha.client.client import Client
    from zha.client.gateway import Gateway


class Device(Remote, EventBase):
    """Client model of a server device."""

    def __init__(
        self, client: Client, gateway: Gateway, info: ExtendedDeviceInfo
    ) -> None:
        """Initialize the device from an info snapshot."""
        super().__init__()
        self._client = client
        self._gateway = gateway
        self._info = info
        self._available = info.available
        self._firmware_version: str | None = None
        self._target = DeviceTarget(ieee=info.ieee)
        self.platform_entities: dict[tuple[Platform, str], Entity] = {}
        self._sync_entities(info)

    def __repr__(self) -> str:
        """Return a string representation of the device."""
        return f"<{type(self).__name__} {self.ieee} {self.name!r}>"

    @property
    def info(self) -> ExtendedDeviceInfo:
        """Return the last info snapshot."""
        return self._info

    @property
    def gateway(self) -> Gateway:
        """Return the gateway for this device."""
        return self._gateway

    @property
    def ieee(self) -> EUI64:
        """Return ieee address for device."""
        return self._info.ieee

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return str(self._info.ieee)

    @property
    def nwk(self) -> NWK:
        """Return nwk for device."""
        return self._info.nwk

    @property
    def name(self) -> str:
        """Return device name."""
        return self._info.name

    @property
    def manufacturer(self) -> str:
        """Return manufacturer for device."""
        return self._info.manufacturer

    @property
    def model(self) -> str:
        """Return model for device."""
        return self._info.model

    @property
    def quirk_applied(self) -> bool:
        """Return whether a quirk is applied."""
        return self._info.quirk_applied

    @property
    def quirk_class(self) -> str:
        """Return the quirk class."""
        return self._info.quirk_class

    @property
    def exposes_features(self) -> set[str]:
        """Return the exposed quirk features."""
        return self._info.exposes_features

    @property
    def manufacturer_code(self) -> int | None:
        """Return the manufacturer code for the device."""
        return self._info.manufacturer_code

    @property
    def power_source(self) -> str:
        """Return the power source for the device."""
        return self._info.power_source

    @property
    def lqi(self) -> int:
        """Return lqi for device, as of the last snapshot."""
        return self._info.lqi

    @property
    def rssi(self) -> int:
        """Return rssi for device, as of the last snapshot."""
        return self._info.rssi

    @property
    def last_seen(self) -> str:
        """Return last_seen for device, as of the last snapshot."""
        return self._info.last_seen

    @property
    def available(self) -> bool:
        """Return True if device is available."""
        return self._available

    @property
    def device_type(self) -> str:
        """Return the logical device type for the device."""
        return self._info.device_type

    @property
    def is_mains_powered(self) -> bool:
        """Return true if device is mains powered."""
        return self._info.power_source == POWER_MAINS_POWERED

    @property
    def device_automation_triggers(self) -> dict[tuple[str, str], dict[str, str]]:
        """Return the device automation triggers for this device."""
        return self._info.device_automation_triggers

    @property
    def device_automation_commands(self) -> dict[str, list[tuple[str, str]]]:
        """Return a lookup of commands to etype/sub_type."""
        commands: dict[str, list[tuple[str, str]]] = {}
        for etype_subtype, trigger in self.device_automation_triggers.items():
            if command := trigger.get(ATTR_COMMAND):
                commands.setdefault(command, []).append(etype_subtype)
        return commands

    @property
    def zigbee_signature(self) -> dict[str, Any]:
        """Return the zigbee signature for this device."""
        return self._info.signature

    @property
    def is_active_coordinator(self) -> bool:
        """Return true if this device is the active coordinator."""
        return self._info.active_coordinator

    @property
    def firmware_version(self) -> str | None:
        """Return the software version for this device."""
        return self._firmware_version

    def get_platform_entity(self, platform: Platform, unique_id: str) -> Entity:
        """Get a platform entity by unique id."""
        return self.platform_entities[(platform, unique_id)]

    def get_entity(
        self,
        platform: Platform,
        endpoint_id: int | None = None,
        *,
        pick_first: bool = False,
    ) -> Entity:
        """Look up the unique entity matching platform and endpoint filters."""
        matches = [
            entity
            for entity in self.platform_entities.values()
            if platform == entity.PLATFORM
            and (endpoint_id is None or entity.state.endpoint_id == endpoint_id)
        ]
        if not matches or (not pick_first and len(matches) != 1):
            raise LookupError(
                f"Expected {'>=1' if pick_first else '1'} entity matching "
                f"platform={platform!r}, endpoint_id={endpoint_id}; "
                f"found {len(matches)}"
            )
        return matches[0]

    def update_from_info(self, info: ExtendedDeviceInfo) -> None:
        """Replace the snapshot and reconcile entities.

        A rebuilt device (re-interview) arrives with new entities but no
        entity-added events, so added and dropped entities are announced here.
        """
        self._info = info
        self._available = info.available
        added, removed = self._sync_entities(info)

        for entity in removed:
            self.emit(
                DeviceEntityRemovedEvent.event_type,
                DeviceEntityRemovedEvent(
                    platform=entity.PLATFORM, unique_id=entity.unique_id
                ),
            )
        for entity in added:
            self.emit(
                DeviceEntityAddedEvent.event_type,
                DeviceEntityAddedEvent(
                    platform=entity.PLATFORM,
                    unique_id=entity.unique_id,
                    state=entity.state,
                ),
            )

    def _sync_entities(
        self, info: ExtendedDeviceInfo
    ) -> tuple[list[Entity], list[Entity]]:
        current: set[tuple[Platform, str]] = set()
        added: list[Entity] = []
        removed: list[Entity] = []

        for unique_id, state in info.entities.items():
            key = (Platform(state.platform), unique_id)
            current.add(key)
            if key in self.platform_entities:
                self.platform_entities[key].replace_state(state)
            else:
                entity = create_entity(self._client, state)
                self.platform_entities[key] = entity
                added.append(entity)

        for key in list(self.platform_entities):
            if key not in current:
                removed.append(self.platform_entities.pop(key))

        self._sync_firmware_version()
        return added, removed

    def _sync_firmware_version(self) -> None:
        for (platform, _unique_id), entity in self.platform_entities.items():
            if platform is Platform.UPDATE:
                self._firmware_version = entity.state.installed_version  # type: ignore[attr-defined]
                return

    def receive_event(self, event: Any) -> None:
        """Apply a server event to the model, then re-emit it."""
        self._handle_event_protocol(event)
        self.emit(event.event, event)

    def handle_zha_device_entity_added_event(
        self, event: DeviceEntityAddedEvent
    ) -> None:
        """Create the entity the server just added."""
        key = (Platform(event.platform), event.unique_id)
        self.platform_entities[key] = create_entity(self._client, event.state)

    def handle_zha_device_entity_removed_event(
        self, event: DeviceEntityRemovedEvent
    ) -> None:
        """Drop the entity the server just removed."""
        del self.platform_entities[(Platform(event.platform), event.unique_id)]

    def handle_zha_device_updated_event(
        self, event: DeviceFirmwareInfoUpdatedEvent
    ) -> None:
        """Track the firmware version."""
        self._firmware_version = event.new_firmware_version

    def handle_zha_device_availability_changed(
        self, event: DeviceAvailabilityChangedEvent
    ) -> None:
        """Track availability."""
        self._available = event.available

    async def async_get_device_info(self) -> DeviceInfo:
        """Fetch a fresh device description from the server."""
        return await self.async_command("device_info")  # type: ignore[no-any-return]

    async def async_get_extended_device_info(self) -> ExtendedDeviceInfo:
        """Fetch a fresh extended device description from the server."""
        info: ExtendedDeviceInfo = await self.async_command("extended_device_info")
        self.update_from_info(info)
        return info

    async def async_get_diagnostics_json(self) -> dict[str, Any]:
        """Fetch the diagnostics dump from the server."""
        return await self.async_command("get_diagnostics_json")  # type: ignore[no-any-return]

    write_zigbee_attribute = remote(ZigbeeDevice.write_zigbee_attribute)
    issue_cluster_command = remote(ZigbeeDevice.issue_cluster_command)
    async_add_to_group = remote(ZigbeeDevice.async_add_to_group)
    async_remove_from_group = remote(ZigbeeDevice.async_remove_from_group)
    async_add_endpoint_to_group = remote(ZigbeeDevice.async_add_endpoint_to_group)
    async_remove_endpoint_from_group = remote(
        ZigbeeDevice.async_remove_endpoint_from_group
    )
    async_bind_to_group = remote(ZigbeeDevice.async_bind_to_group)
    async_unbind_from_group = remote(ZigbeeDevice.async_unbind_from_group)
