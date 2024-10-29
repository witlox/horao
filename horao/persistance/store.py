import json
from typing import Any, Optional

import redis

from horao.persistance.serialize import HoraoDecoder, HoraoEncoder


class Store:

    def __init__(self, url: Optional[str]):
        if url:
            self.redis = redis.Redis.from_url(url)
        self.memory = {}

    def load(self, key: str) -> Any:
        if hasattr(self, "redis"):
            return json.loads(self.redis.get(key), cls=HoraoDecoder)
        return json.loads(self.memory.get(key), cls=HoraoDecoder)

    def save(self, key: str, value: Any):
        if hasattr(self, "redis"):
            self.redis.set(key, json.dumps(value, cls=HoraoEncoder))
        self.memory[key] = json.dumps(value, cls=HoraoEncoder)
