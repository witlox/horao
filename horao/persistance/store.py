# -*- coding: utf-8 -*-#
"""Storage abstraction."""
import json
import logging
from typing import Any, Dict, Optional

from redis.asyncio import Redis as RedisAIO
from redis import Redis as Redis

from horao.conceptual.decorators import instrument_class_function
from horao.persistance.serialize import HoraoDecoder, HoraoEncoder


class Store:
    """Store is a class that is used to store and load objects from memory or redis."""

    def __init__(self, url: Optional[str] = None) -> None:
        """
        Initialize the store
        :param url: optional url to connect to redis, if not provided, memory will be used
        :return: None
        """
        if url:
            self.redis_aio = RedisAIO.from_url(url)
            self.redis = Redis.from_url(url)
        self.memory: Dict[str, Any] = {}

    async def keys(self) -> Dict[str, Any] | Any:
        """
        Return all keys in the store
        :return: keys
        """
        if hasattr(self, "redis"):
            return await self.redis_aio.keys()
        return self.memory.keys()

    async def values(self) -> Dict[str, Any] | Any:
        """
        Return all values in the store
        :return: values
        """
        if hasattr(self, "redis"):
            return await self.redis_aio.values()
        return self.memory.values()

    async def items(self) -> Dict[str, Any] | Any:
        """
        Return all items in the store
        :return: items
        """
        if hasattr(self, "redis"):
            return await self.redis_aio.items()
        return self.memory.items()

    @instrument_class_function(name="async_load", level=logging.DEBUG)
    async def async_load(self, key: str) -> Any | None:
        """
        Load the object from memory or redis
        :param key: key to structure
        :return: structure or None
        """
        if hasattr(self, "redis"):
            structure = await self.redis_aio.get(key)
            return json.loads(structure, cls=HoraoDecoder) if structure else None
        if key not in self.memory:
            return None
        return json.loads(self.memory[key], cls=HoraoDecoder)

    @instrument_class_function(name="load", level=logging.DEBUG)
    def load(self, key: str) -> Any | None:
        """
        Load the object from memory or redis
        :param key: key to structure
        :return: structure or None
        """
        if hasattr(self, "redis"):
            structure = self.redis.get(key)
            return json.loads(structure, cls=HoraoDecoder) if structure else None  # type: ignore
        if key not in self.memory:
            return None
        return json.loads(self.memory[key], cls=HoraoDecoder)

    @instrument_class_function(name="async_save", level=logging.DEBUG)
    async def async_save(self, key: str, value: Any) -> None:
        """
        Save the object to memory or redis
        :param key: key to structure
        :param value: structure
        :return: None
        """
        if hasattr(self, "redis"):
            await self.redis_aio.set(key, json.dumps(value, cls=HoraoEncoder))
        self.memory[key] = json.dumps(value, cls=HoraoEncoder)

    @instrument_class_function(name="save", level=logging.DEBUG)
    def save(self, key: str, value: Any) -> None:
        """
        Save the object to memory or redis
        :param key: key to structure
        :param value: structure
        :return: None
        """
        if hasattr(self, "redis"):
            self.redis.set(key, json.dumps(value, cls=HoraoEncoder))
        self.memory[key] = json.dumps(value, cls=HoraoEncoder)

    def __del__(self):
        """
        Close the redis connection
        :return: None
        """
        if hasattr(self, "redis"):
            self.redis.close()
        if hasattr(self, "redis_aio"):
            self.redis_aio.close()
