from __future__ import annotations

import os
from redis.asyncio import Redis
from redis.commands.core import Script

class LuaScriptManager:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.scripts_dir = os.path.join(os.path.dirname(__file__), "scripts")
        self._scripts: dict[str, Script] = {}
        # Pre-read script contents to avoid blocking IO during async execution
        self._script_contents: dict[str, str] = {}
        for filename in os.listdir(self.scripts_dir):
            if filename.endswith(".lua"):
                name = filename[:-4]
                with open(os.path.join(self.scripts_dir, filename), "r") as f:
                    self._script_contents[name] = f.read()

    def _load_script(self, name: str) -> Script:
        if name not in self._scripts:
            self._scripts[name] = self.redis.register_script(self._script_contents[name])
        return self._scripts[name]

    async def enqueue_task(self, keys: list[str], args: list) -> tuple:
        return await self._load_script("enqueue_task")(keys=keys, args=args)

    async def claim_task(self, keys: list[str], args: list) -> str | None:
        return await self._load_script("claim_task")(keys=keys, args=args)

    async def complete_task(self, keys: list[str], args: list) -> str:
        return await self._load_script("complete_task")(keys=keys, args=args)

    async def fail_task(self, keys: list[str], args: list) -> str:
        return await self._load_script("fail_task")(keys=keys, args=args)

    async def renew_lease(self, keys: list[str], args: list) -> str:
        return await self._load_script("renew_lease")(keys=keys, args=args)

    async def recover_task(self, keys: list[str], args: list) -> str:
        return await self._load_script("recover_task")(keys=keys, args=args)

    async def promote_scheduled(self, keys: list[str], args: list) -> int:
        return await self._load_script("promote_scheduled")(keys=keys, args=args)

    async def promote_retries(self, keys: list[str], args: list) -> int:
        return await self._load_script("promote_retries")(keys=keys, args=args)
