"""Tests for the ZHA client and server split."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import inspect
from unittest.mock import Mock, call, patch

import zigpy.zcl.foundation as zcl_f

from tests.common import (
    get_entity,
    join_zigpy_device,
    send_attributes_report,
    zigpy_device_from_json,
)
from zha.application import Platform
from zha.application.gateway import Gateway
from zha.application.platforms import (
    ENTITY_REGISTRY,
    GROUP_ENTITY_REGISTRY,
    EntityStateChangedEvent,
)
from zha.client import platforms as client_platforms
from zha.client.client import Client
from zha.client.entity import Entity
from zha.client.platforms import SwitchEntity
from zha.common.commands import COMMAND_CONTRACTS, entity_commands
from zha.server.server import LocalTransport, Server
from zha.zigbee.device import ZigbeeDevice
from zha.zigbee.group import GroupMemberReference

PLUG_1 = "tests/data/devices/ledvance-plug-0x00102101.json"
PLUG_2 = "tests/data/devices/ikea-of-sweden-tretakt-smart-plug-0x02040004.json"


@asynccontextmanager
async def connect(zha_gateway: Gateway) -> AsyncIterator[tuple[Server, Client]]:
    """Start a server on the gateway and connect a client to it."""
    async with Server(zha_gateway) as server, Client(LocalTransport(server)) as client:
        yield server, client


async def join_plug(zha_gateway: Gateway, json_file: str = PLUG_1) -> ZigbeeDevice:
    """Join a smart plug device."""
    zigpy_device = await zigpy_device_from_json(
        zha_gateway.application_controller, json_file
    )
    return await join_zigpy_device(zha_gateway, zigpy_device)


async def test_initial_state(zha_gateway: Gateway) -> None:
    """The client mirrors devices and entity states present at connect."""
    zha_device = await join_plug(zha_gateway)

    async with connect(zha_gateway) as (server, client):
        assert client.connected is True
        assert client.server is server
        assert client.gateway is not None
        assert client.server.gateway is zha_gateway
        assert (
            client.gateway.coordinator_zha_device.ieee
            == zha_gateway.state.node_info.ieee
        )
        assert client.gateway.coordinator_zha_device.is_active_coordinator is True

        device = client.gateway.get_device(zha_device.ieee)
        assert device is not None
        assert device.name == zha_device.name
        assert device.available is True
        assert set(device.platform_entities) == set(zha_device.platform_entities)

        for key, entity in zha_device.platform_entities.items():
            assert device.platform_entities[key].state == entity.state
            assert device.platform_entities[key].identifiers == entity.identifiers

        switch = get_entity(zha_device, Platform.SWITCH)
        client_switch = device.get_platform_entity(Platform.SWITCH, switch.unique_id)
        assert isinstance(client_switch, SwitchEntity)
        assert client_switch.PLATFORM is Platform.SWITCH
        assert client_switch.unique_id == switch.unique_id

    assert client.connected is False
    assert client.gateway is None


async def test_state_changes_propagate(zha_gateway: Gateway) -> None:
    """Entity state diffs reach the client and its subscribers."""
    zha_device = await join_plug(zha_gateway)

    async with connect(zha_gateway) as (_server, client):
        switch = get_entity(zha_device, Platform.SWITCH)
        client_switch = client.gateway.devices[zha_device.ieee].get_platform_entity(
            Platform.SWITCH, switch.unique_id
        )
        initial = bool(client_switch.state.is_on)

        listener = Mock()
        client_switch.subscribe_state(listener)
        assert listener.mock_calls == [
            call(
                EntityStateChangedEvent(
                    **client_switch.identifiers.__dict__,
                    state_diff=dict(client_switch.state.__dict__),
                )
            )
        ]
        listener.reset_mock()

        cluster = zha_device.device.endpoints[1].on_off
        await send_attributes_report(zha_gateway, cluster, {0: int(not initial)})

        assert bool(switch.state.is_on) is not initial
        assert client_switch.state == switch.state
        assert listener.mock_calls == [
            call(
                EntityStateChangedEvent(
                    **client_switch.identifiers.__dict__,
                    state_diff={"is_on": switch.state.is_on},
                )
            )
        ]


async def test_entity_command(zha_gateway: Gateway) -> None:
    """A client entity command runs on the server entity."""
    zha_device = await join_plug(zha_gateway)

    async with connect(zha_gateway) as (_server, client):
        switch = get_entity(zha_device, Platform.SWITCH)
        client_switch = client.gateway.devices[zha_device.ieee].get_platform_entity(
            Platform.SWITCH, switch.unique_id
        )
        cluster = zha_device.device.endpoints[1].on_off

        with patch(
            "zigpy.zcl.Cluster.request", return_value=[0x00, zcl_f.Status.SUCCESS]
        ):
            await client_switch.async_turn_on()
            await zha_gateway.async_block_till_done()

            assert cluster.request.mock_calls == [
                call(
                    False,
                    1,
                    cluster.commands_by_name["on"].schema,
                    expect_reply=True,
                    manufacturer=None,
                )
            ]
            assert bool(switch.state.is_on) is True
            assert bool(client_switch.state.is_on) is True


async def test_sync_command_is_fire_and_forget(zha_gateway: Gateway) -> None:
    """Sync commands run on the server without the caller awaiting."""
    zha_device = await join_plug(zha_gateway)

    async with connect(zha_gateway) as (_server, client):
        switch = get_entity(zha_device, Platform.SWITCH)
        client_switch = client.gateway.devices[zha_device.ieee].get_platform_entity(
            Platform.SWITCH, switch.unique_id
        )

        assert switch.enabled is True
        client_switch.disable()
        assert switch.enabled is False
        client_switch.enable()
        assert switch.enabled is True


async def test_device_joins_after_connect(zha_gateway: Gateway) -> None:
    """A device joining after connect appears on the client with its entities."""
    async with connect(zha_gateway) as (_server, client):
        listener = Mock()
        client.gateway.on_event("device_fully_initialized", listener)

        zha_device = await join_plug(zha_gateway)

        device = client.gateway.devices[zha_device.ieee]
        assert set(device.platform_entities) == set(zha_device.platform_entities)
        assert listener.call_count == 2  # CONFIGURED, then INITIALIZED

        # Entity events for the new device are forwarded too
        switch = get_entity(zha_device, Platform.SWITCH)
        cluster = zha_device.device.endpoints[1].on_off
        await send_attributes_report(zha_gateway, cluster, {1: 0, 0: 1, 2: 2})
        assert (
            bool(
                device.get_platform_entity(
                    Platform.SWITCH, switch.unique_id
                ).state.is_on
            )
            is True
        )


async def test_entity_added_and_removed(zha_gateway: Gateway) -> None:
    """Entities added or removed on re-initialization are mirrored."""
    zha_device = await join_plug(zha_gateway)

    async with connect(zha_gateway) as (_server, client):
        device = client.gateway.devices[zha_device.ieee]

        switch = get_entity(zha_device, Platform.SWITCH)
        key = (Platform.SWITCH, switch.unique_id)

        await zha_device._remove_entity(switch, remove=True)
        assert key not in device.platform_entities

        await zha_device.async_initialize(from_cache=True)
        assert key in device.platform_entities
        assert (
            device.platform_entities[key].state
            == zha_device.platform_entities[key].state
        )


async def test_device_availability_and_removal(zha_gateway: Gateway) -> None:
    """Availability changes and device removal are mirrored."""
    zha_device = await join_plug(zha_gateway)

    async with connect(zha_gateway) as (_server, client):
        device = client.gateway.devices[zha_device.ieee]

        assert device.available is True
        zha_device.update_available(False)
        assert device.available is False
        assert all(
            entity.state.available is False
            for entity in device.platform_entities.values()
        )

        zha_gateway.device_removed(zha_device.device)
        await zha_gateway.async_block_till_done()
        assert zha_device.ieee not in client.gateway.devices


async def test_groups(zha_gateway: Gateway) -> None:
    """Groups, members and group entities are mirrored and commandable."""
    device_1 = await join_plug(zha_gateway, PLUG_1)
    device_2 = await join_plug(zha_gateway, PLUG_2)

    async with connect(zha_gateway) as (_server, client):
        members = [
            GroupMemberReference(ieee=device_1.ieee, endpoint_id=1),
            GroupMemberReference(ieee=device_2.ieee, endpoint_id=1),
        ]
        client_group = await client.gateway.async_create_zigpy_group(
            "Test Group", members
        )
        assert client_group is not None
        zha_group = zha_gateway.get_group(client_group.group_id)
        assert zha_group is not None

        assert client.gateway.get_group("Test Group") is client_group
        assert {m.ieee for m in client_group.members} == {
            device_1.ieee,
            device_2.ieee,
        }
        assert client_group.members[0].device is client.gateway.devices[device_1.ieee]
        assert [e.unique_id for e in client_group.members[0].associated_entities] == [
            e.unique_id for e in zha_group.members[0].associated_entities
        ]
        assert set(client_group.group_entities) == set(zha_group.group_entities)

        group_switch = zha_group.group_entities[
            f"switch_zha_group_0x{zha_group.group_id:04x}"
        ]
        client_group_switch = client_group.group_entities[group_switch.unique_id]
        assert client_group_switch.state == group_switch.state

        with patch(
            "zigpy.zcl.Cluster.request", return_value=[0x00, zcl_f.Status.SUCCESS]
        ):
            await client_group_switch.async_turn_on()
            await zha_gateway.async_block_till_done()
            assert zha_group.endpoint.on_off.request.mock_calls == [
                call(
                    False,
                    1,
                    zha_group.endpoint.on_off.commands_by_name["on"].schema,
                    expect_reply=True,
                    manufacturer=None,
                )
            ]

        await client_group.async_remove_members(
            [GroupMemberReference(ieee=device_2.ieee, endpoint_id=1)]
        )
        await zha_gateway.async_block_till_done()
        assert {m.ieee for m in client_group.members} == {device_1.ieee}

        await client.gateway.async_remove_zigpy_group(client_group.group_id)
        await zha_gateway.async_block_till_done()
        assert client_group.group_id not in client.gateway.groups


def test_contracts_cover_server_entities() -> None:
    """Every registered server entity implements the commands it advertises."""
    classes = {cls for classes in ENTITY_REGISTRY.values() for cls in classes}
    classes |= set(GROUP_ENTITY_REGISTRY)

    for cls in classes:
        assert not inspect.isabstract(cls), cls
        for name in entity_commands(cls):
            assert callable(getattr(cls, name)), (cls, name)


def test_contracts_cover_client_entities() -> None:
    """Every contract is forwarded by a concrete client entity, unchanged."""
    client_classes = {
        obj
        for obj in vars(client_platforms).values()
        if inspect.isclass(obj) and issubclass(obj, Entity)
    }

    for contract in COMMAND_CONTRACTS:
        implementations = [cls for cls in client_classes if issubclass(cls, contract)]
        assert implementations, contract

        for cls in implementations:
            assert not inspect.isabstract(cls), cls
            for name in vars(contract):
                if name.startswith("_"):
                    continue
                assert inspect.signature(getattr(cls, name)) == inspect.signature(
                    getattr(contract, name)
                ), (cls, name)
