"""Client-side entity models."""

from __future__ import annotations

from collections.abc import Callable
import dataclasses
import inspect
from typing import TYPE_CHECKING, Any, Concatenate, cast

from zha.application import Platform
from zha.application.platforms import (
    BaseEntityState,
    BaseIdentifiers,
    EntityStateChangedEvent,
    GroupEntityIdentifiers,
    PlatformEntityIdentifiers,
)
from zha.const import STATE_CHANGED
from zha.event import EventBase

if TYPE_CHECKING:
    from zha.client.client import Client


class Remote:
    """An object whose commands are forwarded to the server."""

    _client: Client
    _target: BaseIdentifiers | Any

    async def async_command(self, command: str, **args: Any) -> Any:
        """Send a command to this object's server counterpart and wait."""
        return await self._client.send_command(self._target, command, **args)

    def command_no_wait(self, command: str, **args: Any) -> None:
        """Send a command to this object's server counterpart without waiting."""
        self._client.send_command_no_wait(self._target, command, **args)


def remote[**P, R](
    method: Callable[Concatenate[Any, P], R],
) -> Callable[Concatenate[Any, P], R]:
    """Forward a server method to the client, keeping its signature.

    Coroutine methods wait for the result. Plain methods are fire-and-forget,
    matching how their callers use them today.
    """
    signature = inspect.signature(method)
    name = method.__name__

    def bind(
        self: Remote, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        bound = signature.bind(self, *args, **kwargs)
        arguments = dict(bound.arguments)
        del arguments["self"]
        return arguments

    proxy: Callable[..., Any]

    if inspect.iscoroutinefunction(method):

        async def async_proxy(self: Remote, *args: P.args, **kwargs: P.kwargs) -> Any:
            return await self.async_command(name, **bind(self, args, kwargs))

        proxy = async_proxy
    else:

        def sync_proxy(self: Remote, *args: P.args, **kwargs: P.kwargs) -> None:
            self.command_no_wait(name, **bind(self, args, kwargs))

        proxy = sync_proxy

    proxy.__name__ = name
    proxy.__signature__ = signature  # type: ignore[union-attr]
    proxy.__qualname__ = method.__qualname__
    proxy.__doc__ = method.__doc__
    return cast(Callable[Concatenate[Any, P], R], proxy)


def identifiers_from_state(state: BaseEntityState) -> BaseIdentifiers:
    """Rebuild the server entity's identifiers from its state."""
    if state.group_id is not None:
        return GroupEntityIdentifiers(
            unique_id=state.unique_id,
            platform=state.platform,
            group_id=state.group_id,
        )

    assert state.device_ieee is not None
    return PlatformEntityIdentifiers(
        unique_id=state.unique_id,
        platform=state.platform,
        device_ieee=state.device_ieee,
        endpoint_id=state.endpoint_id,
    )


class Entity(Remote, EventBase):
    """Client model of a server entity."""

    def __init__(self, client: Client, state: BaseEntityState) -> None:
        """Initialize the entity from a state snapshot."""
        super().__init__()
        self._client = client
        self._state = state
        self.identifiers: BaseIdentifiers = identifiers_from_state(state)
        self._target = self.identifiers
        self.PLATFORM = Platform(state.platform)

    def __repr__(self) -> str:
        """Return a string representation of the entity."""
        return f"<{type(self).__name__} {self.unique_id}>"

    @property
    def state(self) -> BaseEntityState:
        """Return the last known state."""
        return self._state

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return self._state.unique_id

    @property
    def available(self) -> bool | None:
        """Return whether the entity is available."""
        return self._state.available

    @property
    def enabled(self) -> bool:
        """Return whether the entity is enabled."""
        return self._state.enabled

    @property
    def primary(self) -> bool:
        """Return whether the entity is the primary device control."""
        return self._state.primary

    def replace_state(self, state: BaseEntityState) -> None:
        """Replace the state with a fresh server snapshot."""
        if state == self._state:
            return
        diff = {
            name: value
            for name, value in state.__dict__.items()
            if self._state.__dict__[name] != value
        }
        self._state = state
        self.emit(
            STATE_CHANGED,
            EntityStateChangedEvent(**self.identifiers.__dict__, state_diff=diff),
        )

    def receive_event(self, event: Any) -> None:
        """Apply a server event to the model, then re-emit it."""
        self._handle_event_protocol(event)
        self.emit(event.event, event)

    def handle_state_changed(self, event: EntityStateChangedEvent) -> None:
        """Apply a state diff."""
        self._state = dataclasses.replace(self._state, **event.state_diff)

    def subscribe_state(
        self, callback: Callable[[EntityStateChangedEvent], None]
    ) -> Callable[[], None]:
        """Subscribe to state changes, receiving the full state as the first event."""
        unsub = self.on_event(STATE_CHANGED, callback)

        try:
            callback(
                EntityStateChangedEvent(
                    **self.identifiers.__dict__,
                    state_diff=dict(self._state.__dict__),
                )
            )
        except Exception:
            unsub()
            raise

        return unsub

    async def async_update(self) -> None:
        """Ask the server entity to refresh its state."""
        await self.async_command("async_update")

    def enable(self) -> None:
        """Enable the entity."""
        self.command_no_wait("enable")

    def disable(self) -> None:
        """Disable the entity."""
        self.command_no_wait("disable")
