import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StreamEvent:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[StreamEvent]] = []

    def subscribe(self) -> asyncio.Queue[StreamEvent]:
        q: asyncio.Queue[StreamEvent] = asyncio.Queue(maxsize=256)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[StreamEvent]) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def publish(self, event: StreamEvent) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


event_bus = EventBus()
