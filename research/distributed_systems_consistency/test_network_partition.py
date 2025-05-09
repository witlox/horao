#!/usr/bin/env python3
"""
Test Case: Network Partition Recovery
Objective: Evaluate consistency recovery after network partition
"""

import asyncio
import logging
import random
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path so we can import HORAO modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from horao.persistance.store import Store

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PartitionableNode:
    """Simulates a HORAO node that can experience network partitions"""

    def __init__(self, node_id: str, partition_group: int = 0):
        self.node_id = node_id
        self.store = Store(f"node_{node_id}")
        self.partition_group = partition_group
        self.connected_nodes: List["PartitionableNode"] = []
        self.partitioned = False

    def connect(self, other_node: "PartitionableNode"):
        """Connect to another node"""
        if other_node not in self.connected_nodes and other_node != self:
            self.connected_nodes.append(other_node)
            other_node.connected_nodes.append(self)

    def disconnect_from_group(self, other_group: int):
        """Disconnect from nodes in the specified group"""
        self.partitioned = True
        logger.info(
            f"Node {self.node_id} (group {self.partition_group}) disconnected from group {other_group}"
        )

    def reconnect(self):
        """Reconnect to all nodes"""
        self.partitioned = False
        logger.info(f"Node {self.node_id} reconnected to all groups")

    async def set_value(self, key: str, value: Any):
        """Set a value in the local store"""
        await self.store.set(key, value)
        logger.info(f"Node {self.node_id} set {key}={value}")

        # Propagate update to connected nodes
        await self.propagate_update(key)

    async def get_value(self, key: str) -> Any:
        """Get a value from the local store"""
        value = await self.store.get(key)
        return value

    async def propagate_update(self, key: str):
        """Propagate update to connected nodes"""
        value = await self.store.get(key)

        for node in self.connected_nodes:
            # Check if we can communicate with this node (partition check)
            if (
                self.partitioned
                and node.partitioned
                and self.partition_group != node.partition_group
            ):
                logger.debug(
                    f"Update from {self.node_id} to {node.node_id} blocked by partition"
                )
                continue

            # Simulate network latency
            await asyncio.sleep(random.uniform(0.01, 0.05))
            await node.receive_update(self.node_id, key, value)

    async def receive_update(self, from_node: str, key: str, value: Any):
        """Handle update received from another node"""
        logger.debug(f"Node {self.node_id} received {key}={value} from {from_node}")
        await self.store.set(key, value)

    def get_state_summary(self) -> Dict[str, Any]:
        """Return a summary of this node's state"""
        return {k: v[0] for k, v in self.store.crdt.data.items()}


async def create_network(num_nodes: int, num_groups: int) -> List[PartitionableNode]:
    """
    Create a network of partitionable nodes

    Args:
        num_nodes: Total number of nodes
        num_groups: Number of partition groups to create

    Returns:
        List of created nodes
    """
    nodes = []
    nodes_per_group = num_nodes // num_groups

    for i in range(num_nodes):
        group = min(i // nodes_per_group, num_groups - 1)
        node = PartitionableNode(f"node_{i}", group)
        nodes.append(node)

    # Connect all nodes in a mesh network
    for i in range(num_nodes):
        for j in range(i + 1, num_nodes):
            nodes[i].connect(nodes[j])

    return nodes


async def run_partition_test(num_nodes: int = 6, num_groups: int = 2):
    """
    Run a test simulating network partition and recovery

    Args:
        num_nodes: Number of nodes to create
        num_groups: Number of partition groups
    """
    logger.info(f"Setting up test with {num_nodes} nodes in {num_groups} groups")

    # Create nodes
    nodes = await create_network(num_nodes, num_groups)

    # Verify initial connectivity by updating a key
    await nodes[0].set_value("initial", "connected")
    await asyncio.sleep(0.2)  # Allow propagation

    # Check initial consistency
    initial_values = [await node.get_value("initial") for node in nodes]
    if len(set(initial_values)) > 1:
        logger.error("Initial consistency check failed!")
        return False

    logger.info("Initial consistency verified. Creating partition...")

    # Create partition between groups
    for node in nodes:
        for g in range(num_groups):
            if g != node.partition_group:
                node.disconnect_from_group(g)

    # Generate updates in each partition
    update_tasks = []
    for g in range(num_groups):
        # Find first node in each group
        for node in nodes:
            if node.partition_group == g:
                update_tasks.append(
                    node.set_value(f"partition_key_{g}", f"value_from_group_{g}")
                )
                break

    await asyncio.gather(*update_tasks)
    await asyncio.sleep(0.2)  # Allow propagation within groups

    # Verify partition worked - nodes should have inconsistent values
    inconsistent = False
    for g in range(num_groups):
        key = f"partition_key_{g}"
        group_values = {}

        for node in nodes:
            value = await node.get_value(key)
            group = node.partition_group
            if group not in group_values:
                group_values[group] = []
            group_values[group].append(value)

        # Check if different groups have different values
        unique_values = {
            tuple(values)
            for values in group_values.values()
            if any(v is not None for v in values)
        }
        if len(unique_values) > 1:
            inconsistent = True
            logger.info(
                f"Partition confirmed: Key {key} has different values across groups"
            )

    if not inconsistent:
        logger.warning("Partition may not have occurred correctly")

    logger.info("Healing partition...")

    # Heal the partition
    for node in nodes:
        node.reconnect()

    # Allow time for consistency recovery
    await asyncio.sleep(0.5)

    # Check if consistency has recovered
    recovered_consistency = True
    for g in range(num_groups):
        key = f"partition_key_{g}"
        values = [await node.get_value(key) for node in nodes]
        unique_values = set(v for v in values if v is not None)

        if len(unique_values) > 1:
            recovered_consistency = False
            logger.error(f"Consistency recovery failed for {key}: {unique_values}")
        elif len(unique_values) == 1:
            logger.info(f"Consistency recovered for {key}: {next(iter(unique_values))}")

    # Final state check
    node_states = [node.get_state_summary() for node in nodes]
    state_match = all(state == node_states[0] for state in node_states)

    logger.info(f"Final consistency check: {'PASS' if state_match else 'FAIL'}")

    return {
        "partition_created_successfully": inconsistent,
        "consistency_recovered": recovered_consistency,
        "final_state_consistent": state_match,
        "final_state": node_states[0],
    }


async def main():
    """Run multiple tests with different configurations"""
    logger.info("Starting network partition test suite")

    # Test with different node counts and group configurations
    configs = [
        (6, 2),  # 6 nodes in 2 groups
        (9, 3),  # 9 nodes in 3 groups
    ]

    for nodes, groups in configs:
        logger.info(f"\n--- Test with {nodes} nodes in {groups} groups ---")
        result = await run_partition_test(nodes, groups)

        print(f"Results for {nodes} nodes in {groups} groups:")
        print(
            f"  - Partition Created: {'Yes' if result['partition_created_successfully'] else 'No'}"
        )
        print(
            f"  - Consistency Recovered: {'Yes' if result['consistency_recovered'] else 'No'}"
        )
        print(
            f"  - Final State Consistent: {'Yes' if result['final_state_consistent'] else 'No'}"
        )
        print(f"  - Final State: {result['final_state']}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
