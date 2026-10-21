"""Per-platform client entities, forwarding the shared command contracts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from zha.application import Platform
from zha.application.platforms.infrared.const import InfraredDeviceClass
from zha.client.entity import Entity, remote
from zha.common.commands import (
    AlarmControlPanelCommands,
    ButtonCommands,
    ClimateCommands,
    CoverCommands,
    FanCommands,
    InfraredEmitterCommands,
    LightCommands,
    LockCommands,
    NumberCommands,
    SelectCommands,
    SirenCommands,
    SwitchCommands,
    UpdateCommands,
    ValveCommands,
)

if TYPE_CHECKING:
    from zha.application.platforms import BaseEntityState
    from zha.client.client import Client


class AlarmControlPanelEntity(Entity, AlarmControlPanelCommands):
    """Client alarm control panel entity."""

    async_alarm_disarm = remote(AlarmControlPanelCommands.async_alarm_disarm)
    async_alarm_arm_home = remote(AlarmControlPanelCommands.async_alarm_arm_home)
    async_alarm_arm_away = remote(AlarmControlPanelCommands.async_alarm_arm_away)
    async_alarm_arm_night = remote(AlarmControlPanelCommands.async_alarm_arm_night)
    async_alarm_trigger = remote(AlarmControlPanelCommands.async_alarm_trigger)


class ButtonEntity(Entity, ButtonCommands):
    """Client button entity."""

    async_press = remote(ButtonCommands.async_press)


class ClimateEntity(Entity, ClimateCommands):
    """Client climate entity."""

    async_set_fan_mode = remote(ClimateCommands.async_set_fan_mode)
    async_set_hvac_mode = remote(ClimateCommands.async_set_hvac_mode)
    async_set_preset_mode = remote(ClimateCommands.async_set_preset_mode)
    async_set_temperature = remote(ClimateCommands.async_set_temperature)


class CoverEntity(Entity, CoverCommands):
    """Client cover entity."""

    async_open_cover = remote(CoverCommands.async_open_cover)
    async_close_cover = remote(CoverCommands.async_close_cover)
    async_set_cover_position = remote(CoverCommands.async_set_cover_position)
    async_stop_cover = remote(CoverCommands.async_stop_cover)
    async_open_cover_tilt = remote(CoverCommands.async_open_cover_tilt)
    async_close_cover_tilt = remote(CoverCommands.async_close_cover_tilt)
    async_set_cover_tilt_position = remote(CoverCommands.async_set_cover_tilt_position)
    async_stop_cover_tilt = remote(CoverCommands.async_stop_cover_tilt)
    restore_external_state_attributes = remote(
        CoverCommands.restore_external_state_attributes
    )


class FanEntity(Entity, FanCommands):
    """Client fan entity."""

    async_turn_on = remote(FanCommands.async_turn_on)
    async_turn_off = remote(FanCommands.async_turn_off)
    async_set_percentage = remote(FanCommands.async_set_percentage)
    async_set_preset_mode = remote(FanCommands.async_set_preset_mode)


class InfraredEmitterEntity(Entity, InfraredEmitterCommands):
    """Client infrared emitter entity."""

    async_send_command = remote(InfraredEmitterCommands.async_send_command)


class InfraredReceiverEntity(Entity):
    """Client infrared receiver entity."""


class LightEntity(Entity, LightCommands):
    """Client light entity."""

    async_turn_on = remote(LightCommands.async_turn_on)
    async_turn_off = remote(LightCommands.async_turn_off)
    restore_external_state_attributes = remote(
        LightCommands.restore_external_state_attributes
    )


class LockEntity(Entity, LockCommands):
    """Client lock entity."""

    async_lock = remote(LockCommands.async_lock)
    async_unlock = remote(LockCommands.async_unlock)
    async_set_lock_user_code = remote(LockCommands.async_set_lock_user_code)
    async_enable_lock_user_code = remote(LockCommands.async_enable_lock_user_code)
    async_disable_lock_user_code = remote(LockCommands.async_disable_lock_user_code)
    async_clear_lock_user_code = remote(LockCommands.async_clear_lock_user_code)
    restore_external_state_attributes = remote(
        LockCommands.restore_external_state_attributes
    )


class NumberEntity(Entity, NumberCommands):
    """Client number entity."""

    async_set_native_value = remote(NumberCommands.async_set_native_value)


class SelectEntity(Entity, SelectCommands):
    """Client select entity."""

    async_select_option = remote(SelectCommands.async_select_option)
    restore_external_state_attributes = remote(
        SelectCommands.restore_external_state_attributes
    )


class SirenEntity(Entity, SirenCommands):
    """Client siren entity."""

    async_turn_on = remote(SirenCommands.async_turn_on)
    async_turn_off = remote(SirenCommands.async_turn_off)
    async_squawk = remote(SirenCommands.async_squawk)


class SwitchEntity(Entity, SwitchCommands):
    """Client switch entity."""

    async_turn_on = remote(SwitchCommands.async_turn_on)
    async_turn_off = remote(SwitchCommands.async_turn_off)


class UpdateEntity(Entity, UpdateCommands):
    """Client firmware update entity."""

    async_install = remote(UpdateCommands.async_install)


class ValveEntity(Entity, ValveCommands):
    """Client valve entity."""

    async_open_valve = remote(ValveCommands.async_open_valve)
    async_close_valve = remote(ValveCommands.async_close_valve)
    async_set_valve_position = remote(ValveCommands.async_set_valve_position)
    async_stop_valve = remote(ValveCommands.async_stop_valve)


ENTITY_CLASSES: dict[Platform, type[Entity]] = {
    Platform.ALARM_CONTROL_PANEL: AlarmControlPanelEntity,
    Platform.BINARY_SENSOR: Entity,
    Platform.BUTTON: ButtonEntity,
    Platform.CLIMATE: ClimateEntity,
    Platform.COVER: CoverEntity,
    Platform.DEVICE_TRACKER: Entity,
    Platform.EVENT: Entity,
    Platform.FAN: FanEntity,
    Platform.LIGHT: LightEntity,
    Platform.LOCK: LockEntity,
    Platform.NUMBER: NumberEntity,
    Platform.SELECT: SelectEntity,
    Platform.SENSOR: Entity,
    Platform.SIREN: SirenEntity,
    Platform.SWITCH: SwitchEntity,
    Platform.VALVE: ValveEntity,
    Platform.VIRTUAL: Entity,
    Platform.UPDATE: UpdateEntity,
}


def create_entity(client: Client, state: BaseEntityState) -> Entity:
    """Create the client entity matching a server entity state."""
    platform = Platform(state.platform)

    if platform is Platform.INFRARED:
        if state.device_class == InfraredDeviceClass.EMITTER:
            return InfraredEmitterEntity(client, state)
        return InfraredReceiverEntity(client, state)

    return ENTITY_CLASSES[platform](client, state)
