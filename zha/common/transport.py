"""Transport interface between the ZHA client and server."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from zha.common.messages import CommandMessage, EventMessage


class Transport(Protocol):
    """Blind RPC: commands go one way, events come back the other."""

    async def send_command(self, message: CommandMessage) -> Any:
        """Send a command and return its result, or raise."""

    def send_command_no_wait(self, message: CommandMessage) -> None:
        """Send a command without waiting for its result."""

    def subscribe(self, callback: Callable[[EventMessage], None]) -> Callable[[], None]:
        """Register a callback for server events and return an unsubscribe."""
