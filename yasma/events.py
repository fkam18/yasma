import asyncio
import json
from typing import Dict

class EventManager:
    def __init__(self):
        self._queues: Dict[int, asyncio.Queue] = {}  # id -> queue
        self._counter = 0

    async def subscribe(self) -> (int, asyncio.Queue):
        self._counter += 1
        q = asyncio.Queue()
        self._queues[self._counter] = q
        return self._counter, q

    def unsubscribe(self, client_id: int):
        self._queues.pop(client_id, None)

    async def publish(self, event: dict):
        data = json.dumps(event)
        for q in list(self._queues.values()):
            await q.put(data)
