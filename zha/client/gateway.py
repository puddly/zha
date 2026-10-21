"""Client-side gateway model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from zigpy.types.named import EUI64

from zha.application.gateway import DeviceFullInitEvent, DeviceRemovedEvent, GroupEvent
from zha.client.device import Device
from zha.client.entity import Remote
from zha.client.group import Group
from zha.common.messages import GatewayTarget, InitialState
from zha.event import EventBase
from zha.zigbee.group import GroupMemberReference

if TYPE_CHECKING:
    from zha.client.client import Client


class Gateway(Remote, EventBase):
    """Client model of the server gateway."""

    def __init__(self, client: Client, initial: InitialState) -> None:
        """Build the model tree from the initial state."""
        super().__init__()
        self._client = client
        self._target = GatewayTarget()
        self.devices: dict[EUI64, Device] = {
            info.ieee: Device(client, self, info) for info in initial.devices
        }
        self.groups: dict[int, Group] = {
            info.group_id: Group(client, self, info) for info in initial.groups
        }
        self.coordinator_zha_device: Device = self.devices[initial.coordinator_ieee]

    def get_device(self, ieee: EUI64) -> Device | None:
        """Return Device for given ieee."""
        return self.devices.get(ieee)

    def get_group(self, group_id_or_name: int | str) -> Group | None:
        """Return Group for given group id or group name."""
        if isinstance(group_id_or_name, str):
            for group in self.groups.values():
                if group.name == group_id_or_name:
                    return group
            return None
        return self.groups.get(group_id_or_name)

    def receive_event(self, event: Any) -> None:
        """Apply a server event to the model, then re-emit it."""
        self._handle_event_protocol(event)
        self.emit(event.event, event)

    def handle_device_fully_initialized(self, event: DeviceFullInitEvent) -> None:
        """Create or refresh the device from its snapshot."""
        info = event.device_info
        if info.ieee in self.devices:
            self.devices[info.ieee].update_from_info(info)
        else:
            self.devices[info.ieee] = Device(self._client, self, info)

    def handle_device_removed(self, event: DeviceRemovedEvent) -> None:
        """Drop the removed device."""
        del self.devices[event.device_info.ieee]

    def handle_group_added(self, event: GroupEvent) -> None:
        """Create the group from its snapshot."""
        self._update_group(event)

    def handle_group_member_added(self, event: GroupEvent) -> None:
        """Refresh the group from its snapshot."""
        self._update_group(event)

    def handle_group_member_removed(self, event: GroupEvent) -> None:
        """Refresh the group from its snapshot."""
        self._update_group(event)

    def handle_group_removed(self, event: GroupEvent) -> None:
        """Drop the removed group."""
        del self.groups[event.group_info.group_id]

    def _update_group(self, event: GroupEvent) -> None:
        info = event.group_info
        if info.group_id in self.groups:
            self.groups[info.group_id].update_from_info(info)
        else:
            self.groups[info.group_id] = Group(self._client, self, info)

    async def async_create_zigpy_group(
        self,
        name: str,
        members: list[GroupMemberReference] | None,
        group_id: int | None = None,
    ) -> Group | None:
        """Create a new Zigbee group."""
        created_id: int | None = await self.async_command(
            "async_create_zigpy_group", name=name, members=members, group_id=group_id
        )
        if created_id is None or created_id not in self.groups:
            return None
        return self.groups[created_id]

    async def async_remove_zigpy_group(self, group_id: int) -> None:
        """Remove a Zigbee group."""
        await self.async_command("async_remove_zigpy_group", group_id=group_id)

    async def async_reinterview_device(self, ieee: EUI64) -> None:
        """Re-interview a device."""
        await self.async_command("async_reinterview_device", ieee=ieee)

    async def async_remove_device(self, ieee: EUI64) -> None:
        """Remove a device from ZHA."""
        await self.async_command("async_remove_device", ieee=ieee)
