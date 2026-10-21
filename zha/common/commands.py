"""Entity command contracts shared by server entities and client proxies.

Each ABC declares the commands a platform accepts. Server entities inherit
the ABC and implement the methods; client entities inherit the same ABC and
forward each method over the transport. Mypy checks both sides against the
same signatures, and the server only dispatches commands declared here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from zha.application.platforms.climate.const import HVACMode
    from zha.application.platforms.cover.const import CoverState
    from zha.application.platforms.infrared import InfraredSignal
    from zha.application.platforms.light.const import ColorMode, FlashMode
    from zha.application.platforms.siren import SquawkMode


class AlarmControlPanelCommands(ABC):
    """Commands accepted by alarm control panel entities."""

    @abstractmethod
    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""

    @abstractmethod
    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""

    @abstractmethod
    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""

    @abstractmethod
    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Send arm night command."""

    @abstractmethod
    async def async_alarm_trigger(self, code: str | None = None) -> None:
        """Send alarm trigger command."""


class ButtonCommands(ABC):
    """Commands accepted by button entities."""

    @abstractmethod
    async def async_press(self) -> None:
        """Press the button."""


class ClimateCommands(ABC):
    """Commands accepted by climate entities."""

    @abstractmethod
    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""

    @abstractmethod
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target operation mode."""

    @abstractmethod
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""

    @abstractmethod
    async def async_set_temperature(
        self,
        target_temp_low: float | None = None,
        target_temp_high: float | None = None,
        temperature: float | None = None,
        hvac_mode: HVACMode | None = None,
    ) -> None:
        """Set new target temperature."""


class CoverCommands(ABC):
    """Commands accepted by cover entities."""

    @abstractmethod
    async def async_open_cover(self) -> None:
        """Open the cover."""

    @abstractmethod
    async def async_close_cover(self) -> None:
        """Close the cover."""

    @abstractmethod
    async def async_set_cover_position(self, position: int) -> None:
        """Move the cover to a specific position."""

    @abstractmethod
    async def async_stop_cover(self) -> None:
        """Stop the cover."""

    @abstractmethod
    async def async_open_cover_tilt(self) -> None:
        """Open the cover tilt."""

    @abstractmethod
    async def async_close_cover_tilt(self) -> None:
        """Close the cover tilt."""

    @abstractmethod
    async def async_set_cover_tilt_position(self, tilt_position: int) -> None:
        """Move the cover tilt to a specific position."""

    @abstractmethod
    async def async_stop_cover_tilt(self) -> None:
        """Stop the cover tilt."""

    @abstractmethod
    def restore_external_state_attributes(
        self,
        *,
        state: CoverState | None,
    ) -> None:
        """Restore external state attributes."""


class FanCommands(ABC):
    """Commands accepted by fan entities."""

    @abstractmethod
    async def async_turn_on(
        self,
        speed: str | None = None,
        percentage: int | None = None,
        preset_mode: str | None = None,
    ) -> None:
        """Turn the entity on."""

    @abstractmethod
    async def async_turn_off(self) -> None:
        """Turn the entity off."""

    @abstractmethod
    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""

    @abstractmethod
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode for the fan."""


class InfraredEmitterCommands(ABC):
    """Commands accepted by infrared emitter entities."""

    @abstractmethod
    async def async_send_command(self, signal: InfraredSignal) -> None:
        """Transmit a raw infrared signal."""


class LightCommands(ABC):
    """Commands accepted by light entities."""

    @abstractmethod
    async def async_turn_on(
        self,
        *,
        transition: float | None = None,
        brightness: int | None = None,
        effect: str | None = None,
        flash: FlashMode | None = None,
        color_temp: int | None = None,
        xy_color: tuple[float, float] | None = None,
    ) -> None:
        """Turn the entity on."""

    @abstractmethod
    async def async_turn_off(self, *, transition: float | None = None) -> None:
        """Turn the entity off."""

    @abstractmethod
    def restore_external_state_attributes(
        self,
        *,
        state: bool | None,
        off_with_transition: bool | None,
        off_brightness: int | None,
        brightness: int | None,
        color_temp: int | None,
        xy_color: tuple[float, float] | None,
        color_mode: ColorMode | None,
        effect: str | None,
    ) -> None:
        """Restore extra state attributes that are stored outside of the ZCL cache."""


class LockCommands(ABC):
    """Commands accepted by lock entities."""

    @abstractmethod
    async def async_lock(self) -> None:
        """Lock the lock."""

    @abstractmethod
    async def async_unlock(self) -> None:
        """Unlock the lock."""

    @abstractmethod
    async def async_set_lock_user_code(self, code_slot: int, user_code: str) -> None:
        """Set the user_code to index X on the lock."""

    @abstractmethod
    async def async_enable_lock_user_code(self, code_slot: int) -> None:
        """Enable user_code at index X on the lock."""

    @abstractmethod
    async def async_disable_lock_user_code(self, code_slot: int) -> None:
        """Disable user_code at index X on the lock."""

    @abstractmethod
    async def async_clear_lock_user_code(self, code_slot: int) -> None:
        """Clear the user_code at index X on the lock."""

    @abstractmethod
    def restore_external_state_attributes(
        self,
        *,
        state: Literal["locked", "unlocked"] | None,
    ) -> None:
        """Restore external state attributes."""


class NumberCommands(ABC):
    """Commands accepted by number entities."""

    @abstractmethod
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""


class SelectCommands(ABC):
    """Commands accepted by select entities."""

    @abstractmethod
    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""

    @abstractmethod
    def restore_external_state_attributes(
        self,
        *,
        state: str,
    ) -> None:
        """Restore external state attributes."""


class SirenCommands(ABC):
    """Commands accepted by siren entities."""

    @abstractmethod
    async def async_turn_on(
        self,
        duration: int | None = None,
        tone: int | None = None,
        volume_level: int | None = None,
        # These kwargs are ZHA extensions to the base HA entity signature
        strobe: int | None = None,
        strobe_duty_cycle: int | None = None,
        strobe_intensity: int | None = None,
    ) -> None:
        """Turn on siren."""

    @abstractmethod
    async def async_turn_off(self) -> None:
        """Turn off siren."""

    # This method is a ZHA extension to the base HA siren entity
    @abstractmethod
    async def async_squawk(
        self,
        *,
        mode: SquawkMode,
        strobe: int,
        squawk_level: int,
    ) -> None:
        """Issue a brief squawk pulse."""


class SwitchCommands(ABC):
    """Commands accepted by switch entities."""

    @abstractmethod
    async def async_turn_on(self) -> None:
        """Turn the entity on."""

    @abstractmethod
    async def async_turn_off(self) -> None:
        """Turn the entity off."""


class UpdateCommands(ABC):
    """Commands accepted by firmware update entities."""

    @abstractmethod
    async def async_install(self, version: str | None) -> None:
        """Install an update."""


class ValveCommands(ABC):
    """Commands accepted by valve entities."""

    @abstractmethod
    async def async_open_valve(self) -> None:
        """Open the valve."""

    @abstractmethod
    async def async_close_valve(self) -> None:
        """Close the valve."""

    @abstractmethod
    async def async_set_valve_position(self, position: int) -> None:
        """Move the valve to a specific position."""

    @abstractmethod
    async def async_stop_valve(self) -> None:
        """Stop the valve."""


COMMAND_CONTRACTS: tuple[type[ABC], ...] = (
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

# Commands every entity accepts, defined on `BaseEntity` rather than a contract
BASE_ENTITY_COMMANDS: frozenset[str] = frozenset({"async_update", "enable", "disable"})


def entity_commands(entity_cls: type) -> frozenset[str]:
    """Return the command names an entity class accepts."""
    names: set[str] = set(BASE_ENTITY_COMMANDS)
    for cls in entity_cls.__mro__:
        if cls in COMMAND_CONTRACTS:
            names |= {name for name in vars(cls) if not name.startswith("_")}
    return frozenset(names)
