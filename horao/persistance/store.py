# -*- coding: utf-8 -*-#
import json
import logging
from typing import Any, Optional

import redis

from horao.conceptual.decorators import instrument_class_function
from horao.persistance.serialize import HoraoDecoder, HoraoEncoder


class Store:
    """Store is a class that is used to store and load objects from memory or redis."""

    def __init__(self, url: Optional[str]) -> None:
        """
        Initialize the store
        :param url: optional url to connect to redis, if not provided, memory will be used
        :return: None
        """
        if url:
            self.redis = redis.Redis.from_url(url)
        self.memory = {}

    @instrument_class_function(name="load", level=logging.DEBUG)
    def load(self, key: str) -> Any:
        """
        Load the object from memory or redis
        :param key: key to structure
        :return: structure
        """
        if hasattr(self, "redis"):
            return json.loads(self.redis.get(key), cls=HoraoDecoder)
        return json.loads(self.memory[key], cls=HoraoDecoder)

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
