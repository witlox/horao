from __future__ import annotations

from dataclasses import dataclass, field

from horao.physical.storage import StorageClass, StorageType


@dataclass
class ResourceDefinition:
    """Base class for resource definitions."""

    amount: int = field(default=1)


class Compute(ResourceDefinition):
    """Represents a compute resource."""

    def __init__(
        self, cpu: int, ram: int, accelerator: bool, amount: int = None
    ) -> None:
        """
        Initialize the compute resource.
        :param cpu: amount of CPUs per node
        :param ram: amount of RAM in GB per node
        :param accelerator: requires an accelerator
        :param amount: total amount of nodes
        """
        super().__init__(amount)
        self.cpu = cpu
        self.ram = ram
        self.accelerator = accelerator

    def __eq__(self, other: Compute) -> bool:
        return (
            super().__eq__(other)
            and self.cpu == other.cpu
            and self.ram == other.ram
            and self.accelerator == other.accelerator
        )

    def __hash__(self):
        return hash((self.amount, self.cpu, self.ram, self.accelerator))


class Storage(ResourceDefinition):
    """Represents a storage resource."""

    def __init__(
        self, capacity: int, storage_type: StorageType, storage_class: StorageClass
    ) -> None:
        """
        Initialize the storage resource.
        :param capacity: total capacity in TB
        :param storage_type: type of storage
        :param storage_class: class of storage
        """
        super().__init__(capacity)
        self.storage_type = storage_type
        self.storage_class = storage_class

    def __eq__(self, other: Storage) -> bool:
        return (
            super().__eq__(other)
            and self.storage_type == other.storage_type
            and self.storage_class == other.storage_class
        )

    def __hash__(self):
        return hash((self.amount, self.storage_type, self.storage_class))
