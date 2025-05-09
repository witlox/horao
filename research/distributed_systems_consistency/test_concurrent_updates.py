#!/usr/bin/env python3
"""
Test Case: Concurrent Updates
Objective: Measure consistency during high-frequency concurrent updates
"""

import asyncio
import logging
import random
import sys
import time
from pathlib import Path
from typing import Any, List

# Add project root to path so we can import HORAO modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from horao.persistance.store import Store

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Node:
    """Simulates a HORAO node for testing"""

    def __init__(self, node_id: str, network_latency: float = 0.05):
        self.node_id = node_id
        self.store = Store(f"node_{node_id}")
        self.network_latency = network_latency
        self.connected_nodes: List[Node] = []

    def connect(self, other_node: "Node"):
        """Connect to another node"""
        if other_node not in self.connected_nodes and other_node != self:
            self.connected_nodes.append(other_node)
            other_node.connected_nodes.append(self)

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
            # Simulate network latency
            await asyncio.sleep(random.uniform(0, self.network_latency))
            await node.receive_update(self.node_id, key, value)

    async def receive_update(self, from_node: str, key: str, value: Any):
        """Handle update received from another node"""
        logger.debug(f"Node {self.node_id} received {key}={value} from {from_node}")
        await self.store.set(key, value)


async def run_concurrent_updates_test(
    num_nodes: int = 5, updates_per_node: int = 20, network_latency: float = 0.05
):
    """
    Run test with concurrent updates across multiple nodes

    Args:
        num_nodes: Number of nodes to create
        updates_per_node: Number of updates to perform per node
        network_latency: Maximum network latency between nodes (in seconds)
    """
    logger.info(
        f"Setting up test with {num_nodes} nodes, {updates_per_node} updates each"
    )

    # Create nodes
    nodes = [Node(f"node_{i}", network_latency) for i in range(num_nodes)]

    # Connect nodes in a mesh network
    for i in range(num_nodes):
        for j in range(i + 1, num_nodes):
            nodes[i].connect(nodes[j])

    # Perform concurrent updates
    start_time = time.time()
    tasks = []

    for node_idx, node in enumerate(nodes):
        for update_idx in range(updates_per_node):
            # Each node updates its own key with a unique value
            key = f"key_{update_idx}"
            value = f"value_from_node_{node_idx}_update_{update_idx}"
            tasks.append(node.set_value(key, value))

    # Wait for all updates to be initiated
    await asyncio.gather(*tasks)

    # Allow time for propagation
    propagation_time = (
        network_latency * 3 * num_nodes
    )  # Estimate based on network topology
    logger.info(f"Waiting {propagation_time:.2f}s for propagation to complete")
    await asyncio.sleep(propagation_time)

    # Verify consistency
    inconsistencies = 0
    for update_idx in range(updates_per_node):
        key = f"key_{update_idx}"
        values = []

        for node in nodes:
            value = await node.get_value(key)
            values.append(value)

        # Check if all nodes have the same value for this key
        if len(set(values)) > 1:
            inconsistencies += 1
            logger.warning(f"Inconsistency detected for {key}: {values}")

    total_time = time.time() - start_time
    consistency_rate = (1 - inconsistencies / updates_per_node) * 100

    logger.info(f"Test completed in {total_time:.2f}s")
    logger.info(f"Consistency rate: {consistency_rate:.2f}%")
    logger.info(f"Inconsistencies: {inconsistencies}/{updates_per_node}")

    return {
        "total_time": total_time,
        "consistency_rate": consistency_rate,
        "inconsistencies": inconsistencies,
        "total_updates": updates_per_node,
    }


async def main():
    """Run the test suite with various parameters"""
    logger.info("Starting concurrent updates test suite")

    # Test with different node counts
    for num_nodes in [3, 5, 10]:
        # Test with different network latencies
        for latency in [0.01, 0.05, 0.1]:
            logger.info(
                f"\n--- Test with {num_nodes} nodes, {latency}s network latency ---"
            )
            result = await run_concurrent_updates_test(num_nodes, 20, latency)

            print(f"Results for {num_nodes} nodes, {latency}s latency:")
            print(f"  - Consistency Rate: {result['consistency_rate']:.2f}%")
            print(f"  - Total Time: {result['total_time']:.2f}s")
            print(
                f"  - Inconsistencies: {result['inconsistencies']}/{result['total_updates']}"
            )
            print()


if __name__ == "__main__":
    asyncio.run(main())
