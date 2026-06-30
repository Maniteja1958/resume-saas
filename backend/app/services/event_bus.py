from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, AsyncIterator

from app.services.storage import save_event, list_events, now_iso


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

    async def publish(self, analysis_id: str, event: dict[str, Any]) -> None:
        event = dict(event)
        event.setdefault("created_at", now_iso())
        event.setdefault("analysis_id", analysis_id)
        await save_event(analysis_id, event)

        for queue in list(self._queues.get(analysis_id, [])):
            await queue.put(event)

    async def subscribe(self, analysis_id: str) -> AsyncIterator[dict[str, Any]]:
        # Replay saved events first so refreshes do not lose progress.
        past_events = await list_events(analysis_id)
        for event in past_events:
            yield event
            if event.get("type") in {"done", "error"}:
                return

        queue: asyncio.Queue = asyncio.Queue()
        self._queues[analysis_id].append(queue)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20)
                except asyncio.TimeoutError:
                    yield {
                        "analysis_id": analysis_id,
                        "type": "heartbeat",
                        "message": "still connected",
                        "progress": None,
                        "created_at": now_iso(),
                    }
                    continue
                yield event
                if event.get("type") in {"done", "error"}:
                    break
        finally:
            if queue in self._queues.get(analysis_id, []):
                self._queues[analysis_id].remove(queue)


event_bus = EventBus()
