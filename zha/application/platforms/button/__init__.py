"""Support for ZHA button."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import functools
import logging
from typing import TYPE_CHECKING, Any
import warnings

from zigpy.zcl import Cluster, ClusterType
from zigpy.zcl.clusters.general import Identify

from zha.application import Platform
from zha.application.helpers import write_attributes_safe
from zha.application.platforms import (
    BaseEntityState,
    ClusterMatch,
    EntityCategory,
    PlatformEntity,
    ZclPlatformEntity,
    register_entity,
)
from zha.application.platforms.button.const import DEFAULT_DURATION, ButtonDeviceClass
from zha.application.platforms.const import TUYA_MANUFACTURER_CLUSTER
from zha.application.platforms.legacy_quirks import AQARA_OPPLE_CLUSTER

if TYPE_CHECKING:
    from zha.zigbee.device import Device
    from zha.zigbee.endpoint import Endpoint

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ButtonState(BaseEntityState):
    """State for button entities."""

    pass


@dataclass(frozen=True, kw_only=True)
class CommandButtonState(ButtonState):
    """State for command button entities."""

    command: str
    args: list[Any]
    kwargs: dict[str, Any]


@dataclass(frozen=True, kw_only=True)
class WriteAttributeButtonState(ButtonState):
    """State for write attribute button entities."""

    attribute_name: str
    attribute_value: Any


class BaseButton(PlatformEntity, ABC):
    """Base representation of a ZHA button."""

    PLATFORM = Platform.BUTTON

    @property
    def state(self) -> ButtonState:
        """Return the state of the button."""
        return ButtonState(**super().state.__dict__)

    @abstractmethod
    async def async_press(self) -> None:
        """Send out a press command."""


class Button(BaseButton, ZclPlatformEntity):
    """Defines a ZHA button."""

    _command_name: str
    _args: list[Any]
    _kwargs: dict[str, Any]

    def __init__(
        self,
        endpoint: Endpoint,
        device: Device,
        *,
        command_name: str | None = None,
        command_args: list[Any] | None = None,
        command_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Init this button."""
        if command_name is not None:
            self._command_name = command_name
        if command_args is not None:
            self._args = command_args
        if command_kwargs is not None:
            self._kwargs = command_kwargs

        super().__init__(endpoint=endpoint, device=device, **kwargs)

    @property
    def state(self) -> CommandButtonState:
        """Return the state of the button."""
        return CommandButtonState(
            **super().state.__dict__,
            command=self._command_name,
            args=self._args,
            kwargs=self._kwargs,
        )

    @functools.cached_property
    def args(self) -> list[Any]:
        """Return the arguments to use in the command."""
        return list(self._args) if self._args else []

    @functools.cached_property
    def kwargs(self) -> dict[str, Any]:
        """Return the keyword arguments to use in the command."""
        return self._kwargs

    async def async_press(self) -> None:
        """Send out a update command."""
        command = getattr(self._cluster, self._command_name)
        arguments = self.args or []
        kwargs = self.kwargs or {}
        await command(*arguments, **kwargs)


class IdentifyButton(BaseButton):
    """Defines a ZHA identify button for a device."""

    _attr_device_class = ButtonDeviceClass.IDENTIFY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    _device: Device

    def __init__(self, device: Device, *, cluster: Cluster, **kwargs: Any) -> None:
        """Init the identify button, sending commands to the given Identify cluster."""
        self._cluster = cluster
        super().__init__(device, **kwargs)

    @property
    def device(self) -> Device:
        """Return the device."""
        return self._device

    @staticmethod
    def legacy_identify_cluster(device: Device) -> Cluster | None:
        """Return the Identify cluster the legacy unique ID was derived from."""
        for ep_id, ep in device.endpoints.items():
            if ep_id == 0 or Identify.cluster_id not in ep.zigpy_endpoint.in_clusters:
                continue
            return ep.zigpy_endpoint.in_clusters[Identify.cluster_id]
        return None

    # TODO: remove once zha-quirks only filters `ZclPlatformEntity` by endpoint/cluster
    # and HA Core's `websocket_get_groupable_devices` no longer reads `entity.endpoint`
    @property
    def endpoint(self) -> Endpoint:
        """Return the endpoint of the Identify cluster, for old quirks."""
        warnings.warn(
            f"`{type(self).__name__}.endpoint` is deprecated, device-bound entities"
            " have no endpoint",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._device.endpoints[self._cluster.endpoint.endpoint_id]

    def targets_cluster(
        self, cluster_id: int, cluster_type: ClusterType | None = None
    ) -> bool:
        """Match the Identify cluster, for old quirks."""
        warnings.warn(
            f"`{type(self).__name__}.targets_cluster` is deprecated, device-bound"
            " entities have no cluster",
            DeprecationWarning,
            stacklevel=2,
        )
        return cluster_id == Identify.cluster_id and cluster_type in (
            None,
            ClusterType.Server,
        )

    @property
    def state(self) -> CommandButtonState:
        """Return the state of the button."""
        return CommandButtonState(
            **super().state.__dict__,
            command="identify",
            args=[DEFAULT_DURATION],
            kwargs={},
        )

    async def async_press(self) -> None:
        """Identify the device."""
        await self._cluster.identify(DEFAULT_DURATION)


class WriteAttributeButton(BaseButton, ZclPlatformEntity):
    """Defines a ZHA button, which writes a value to an attribute."""

    _attribute_name: str
    _attribute_value: Any = None

    def __init__(
        self,
        endpoint: Endpoint,
        device: Device,
        *,
        attribute_name: str | None = None,
        attribute_value: Any = None,
        **kwargs: Any,
    ) -> None:
        """Init this button."""
        if attribute_name is not None:
            self._attribute_name = attribute_name
        if attribute_value is not None:
            self._attribute_value = attribute_value

        super().__init__(endpoint=endpoint, device=device, **kwargs)
        self.recompute_capabilities()

    @property
    def state(self) -> WriteAttributeButtonState:
        """Return the state of the button."""
        return WriteAttributeButtonState(
            **super().state.__dict__,
            attribute_name=self._attribute_name,
            attribute_value=self._attribute_value,
        )

    async def async_press(self) -> None:
        """Write attribute with defined value."""
        await write_attributes_safe(
            self._cluster, {self._attribute_name: self._attribute_value}
        )


@register_entity(TUYA_MANUFACTURER_CLUSTER)
class FrostLockResetButton(WriteAttributeButton):
    """Defines a ZHA frost lock reset button."""

    _unique_id_suffix = "reset_frost_lock"
    _attribute_name = "frost_lock_reset"
    _attribute_value = 0
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "reset_frost_lock"
    _cluster_id = TUYA_MANUFACTURER_CLUSTER

    _cluster_match = ClusterMatch(
        server_clusters=frozenset({TUYA_MANUFACTURER_CLUSTER}),
        manufacturers=frozenset({"_TZE200_htnnfasr"}),
    )


@register_entity(AQARA_OPPLE_CLUSTER)
class NoPresenceStatusResetButton(WriteAttributeButton):
    """Defines a ZHA no presence status reset button."""

    _unique_id_suffix = "reset_no_presence_status"
    _attribute_name = "reset_no_presence_status"
    _attribute_value = 1
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "reset_no_presence_status"
    _cluster_id = AQARA_OPPLE_CLUSTER

    _cluster_match = ClusterMatch(
        server_clusters=frozenset({AQARA_OPPLE_CLUSTER}),
        models=frozenset({"lumi.motion.ac01"}),
    )


@register_entity(AQARA_OPPLE_CLUSTER)
class AqaraSelfTestButton(WriteAttributeButton):
    """Defines a ZHA self-test button for Aqara smoke sensors."""

    _unique_id_suffix = "self_test"
    _attribute_name = "self_test"
    _attribute_value = 1
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "self_test"
    _cluster_id = AQARA_OPPLE_CLUSTER

    _cluster_match = ClusterMatch(
        server_clusters=frozenset({AQARA_OPPLE_CLUSTER}),
        models=frozenset({"lumi.sensor_smoke.acn03"}),
    )
