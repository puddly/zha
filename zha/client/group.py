"""Client-side group model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from zigpy.types.named import EUI64

from zha.application import Platform
from zha.client.entity import Entity, Remote, remote
from zha.client.platforms import create_entity
from zha.common.messages import GroupTarget
from zha.zigbee.group import Group as ServerGroup, GroupInfo, GroupMemberInfo

if TYPE_CHECKING:
    from zha.client.client import Client
    from zha.client.device import Device
    from zha.client.gateway import Gateway


class GroupMember:
    """A device endpoint that is a member of a group."""

    def __init__(self, group: Group, info: GroupMemberInfo) -> None:
        """Initialize the group member."""
        self._group = group
        self._info = info

    @property
    def group(self) -> Group:
        """Return the group this member belongs to."""
        return self._group

    @property
    def member_info(self) -> GroupMemberInfo:
        """Return the member snapshot."""
        return self._info

    @property
    def ieee(self) -> EUI64:
        """Return the member device ieee."""
        return self._info.ieee

    @property
    def endpoint_id(self) -> int:
        """Return the endpoint id for this group member."""
        return self._info.endpoint_id

    @property
    def device(self) -> Device:
        """Return the client device for this group member."""
        return self._group.gateway.devices[self._info.ieee]

    @property
    def associated_entities(self) -> list[Entity]:
        """Return the device entities derived from this endpoint."""
        device = self.device
        return [
            device.platform_entities[(Platform(state.platform), unique_id)]
            for unique_id, state in self._info.entities.items()
        ]


class Group(Remote):
    """Client model of a server group."""

    def __init__(self, client: Client, gateway: Gateway, info: GroupInfo) -> None:
        """Initialize the group from an info snapshot."""
        self._client = client
        self._gateway = gateway
        self._info = info
        self._target = GroupTarget(group_id=info.group_id)
        self.group_entities: dict[str, Entity] = {}
        self._sync_entities(info)

    def __repr__(self) -> str:
        """Return a string representation of the group."""
        return f"<{type(self).__name__} 0x{self.group_id:04x} {self.name!r}>"

    @property
    def info(self) -> GroupInfo:
        """Return the last info snapshot."""
        return self._info

    @property
    def gateway(self) -> Gateway:
        """Return the gateway for this group."""
        return self._gateway

    @property
    def group_id(self) -> int:
        """Return group id."""
        return self._info.group_id

    @property
    def name(self) -> str:
        """Return group name."""
        return self._info.name

    @property
    def members(self) -> list[GroupMember]:
        """Return the members of this group."""
        return [GroupMember(self, member) for member in self._info.members]

    def update_from_info(self, info: GroupInfo) -> None:
        """Replace the snapshot and reconcile entities."""
        self._info = info
        self._sync_entities(info)

    def _sync_entities(self, info: GroupInfo) -> None:
        for unique_id, state in info.entities.items():
            if unique_id in self.group_entities:
                self.group_entities[unique_id].replace_state(state)
            else:
                self.group_entities[unique_id] = create_entity(self._client, state)

        for unique_id in list(self.group_entities):
            if unique_id not in info.entities:
                del self.group_entities[unique_id]

    async_add_members = remote(ServerGroup.async_add_members)
    async_remove_members = remote(ServerGroup.async_remove_members)
