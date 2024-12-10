# -*- coding: utf-8 -*-#
"""Storage abstraction."""
import json
import logging
from typing import Any, Dict, Optional

from redis import Redis as Redis
from redis.asyncio import Redis as RedisAIO

from horao.conceptual.decorators import instrument_class_function
from horao.logical.infrastructure import LogicalInfrastructure
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

    async def load_logical_infrastructure(self) -> LogicalInfrastructure:
        """
        Load the logical infrastructure from the store
        :return: LogicalInfrastructure
        """
        infrastructure = {}
        claims = {}
        constraints = {}
        for key in await self.keys():
            if key.startswith("datacenter-"):
                dc = await self.async_load(key)
                content = await self.async_load(f"datacenter-{key}.content")
                infrastructure[dc] = content
            elif key.startswith("claim-"):
                claim = await self.async_load(key)
                content = await self.async_load(f"claim-{key}.content")
                claims[claim] = content
            elif key.startswith("constraint-"):
                constraint = await self.async_load(key)
                content = await self.async_load(f"constraint-{key}.content")
                constraints[constraint] = content
        return LogicalInfrastructure(infrastructure, constraints, claims)

    async def save_logical_infrastructure(
        self, logical_infrastructure: LogicalInfrastructure
    ) -> None:
        """
        Save the logical infrastructure to the store
        :param logical_infrastructure: infrastructure to save
        :return: None
        """
        for k, v in logical_infrastructure.infrastructure.items():
            local_dc = await self.async_load(k.name)
            if not local_dc:
                await self.async_save(f"datacenter-{k.name}", k)
            else:
                local_dc.merge(k)
            local_dc_content = await self.async_load(f"datacenter-{k.name}.content")
            if not local_dc_content:
                await self.async_save(f"datacenter-{k.name}.content", v)
            else:
                local_dc_content.merge(v)
        if logical_infrastructure.claims:
            for k, v in logical_infrastructure.claims.items():  # type: ignore
                await self.async_save(f"claim-{k.name}", k)
                await self.async_save(f"claim-{k.name}.content", v)
        if logical_infrastructure.constraints:
            for k, v in logical_infrastructure.constraints.items():  # type: ignore
                await self.async_save(f"constraint-{k.name}", k)
                await self.async_save(f"constraint-{k.name}.content", v)

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
