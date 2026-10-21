"""Messages exchanged between the ZHA client and server."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from zigpy.types.named import EUI64

from zha.application.platforms import (
    BaseIdentifiers,
    GroupEntityIdentifiers,
    PlatformEntityIdentifiers,
)
from zha.zigbee.device import ExtendedDeviceInfo
from zha.zigbee.group import GroupInfo

START_LISTENING = "start_listening"


@dataclass(frozen=True, kw_only=True)
class GatewayTarget:
    """Addresses the gateway itself."""


@dataclass(frozen=True, kw_only=True)
class DeviceTarget:
    """Addresses a device."""

    ieee: EUI64


@dataclass(frozen=True, kw_only=True)
class GroupTarget:
    """Addresses a group."""

    group_id: int


# Entities are addressed by their existing identifiers
EntityTarget = PlatformEntityIdentifiers | GroupEntityIdentifiers
Target = GatewayTarget | DeviceTarget | GroupTarget | BaseIdentifiers


@dataclass(frozen=True, kw_only=True)
class CommandMessage:
    """A command sent by the client to an object on the server."""

    message_id: str
    target: Target
    command: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class EventMessage:
    """An event emitted by an object on the server."""

    source: Target
    event: Any


@dataclass(frozen=True, kw_only=True)
class InitialState:
    """Full state of the gateway, returned by `start_listening`."""

    coordinator_ieee: EUI64
    devices: list[ExtendedDeviceInfo]
    groups: list[GroupInfo]
