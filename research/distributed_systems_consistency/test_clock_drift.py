#!/usr/bin/env python3
"""
Test Case: Clock Drift Impact
Objective: Measure the impact of clock drift on consistency
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


class DriftingNode:
    """Simulates a HORAO node with drifting clock"""

    def __init__(self, node_id: str, clock_drift: float = 0.0):
        """
        Initialize a node with specified clock drift

        Args:
            node_id: Unique identifier for the node
            clock_drift: Clock drift factor (1.0 = normal speed,
                         2.0 = twice as fast, 0.5 = half speed)
        """
        self.node_id = node_id
        self.store = Store(f"node_{node_id}")
        self.clock_drift = clock_drift
        self.connected_nodes: List["DriftingNode"] = []
        self.start_time = time.time()

    def connect(self, other_node: "DriftingNode"):
        """Connect to another node"""
        if other_node not in self.connected_nodes and other_node != self:
            self.connected_nodes.append(other_node)
            other_node.connected_nodes.append(self)

    def get_logical_time(self) -> float:
        """Get current logical time affected by drift"""
        elapsed = time.time() - self.start_time
        return elapsed * self.clock_drift

    async def set_value(self, key: str, value: Any):
        """Set a value in the local store with current logical time"""
        logical_time = self.get_logical_time()
        await self.store.set(key, value, logical_time)
        logger.info(f"Node {self.node_id} set {key}={value} at time {logical_time:.2f}")

        # Propagate update to connected nodes
        await self.propagate_update(key)

    async def get_value(self, key: str) -> Any:
        """Get a value from the local store"""
        value = await self.store.get(key)
        return value

    async def propagate_update(self, key: str):
        """Propagate update to connected nodes"""
        value = await self.store.get(key)
        timestamp = self.store.crdt.data.get(key, (None, 0))[1]

        for node in self.connected_nodes:
            # Simulate network latency
            await asyncio.sleep(random.uniform(0.01, 0.05))
            await node.receive_update(self.node_id, key, value, timestamp)

    async def receive_update(
        self, from_node: str, key: str, value: Any, timestamp: float
    ):
        """Handle update received from another node"""
        logger.debug(
            f"Node {self.node_id} received {key}={value} (ts={timestamp:.2f}) from {from_node}"
        )

        # Apply the update with the provided timestamp
        current_value = await self.store.get(key)
        current_ts = self.store.crdt.data.get(key, (None, 0))[1]

        if current_value is None or timestamp > current_ts:
            await self.store.set(key, value, timestamp)
            logger.debug(
                f"Node {self.node_id} updated {key}={value} (ts={timestamp:.2f})"
            )
        else:
            logger.debug(
                f"Node {self.node_id} ignored update for {key} (local_ts={current_ts:.2f} > remote_ts={timestamp:.2f})"
            )


async def run_clock_drift_test(
    num_nodes: int = 4, num_updates: int = 50, drift_factors: List[float] = None
):
    """
    Run a test with nodes having different clock drift rates

    Args:
        num_nodes: Number of nodes to create
        num_updates: Number of updates to perform
        drift_factors: List of clock drift factors for each node
    """
    if drift_factors is None:
        # Default: one normal node, two fast nodes, one slow node
        drift_factors = [1.0] + [2.0, 1.5] + [0.5]

    # Ensure we have enough drift factors
    while len(drift_factors) < num_nodes:
        drift_factors.append(1.0)

    logger.info(
        f"Setting up test with {num_nodes} nodes with drift factors: {drift_factors[:num_nodes]}"
    )

    # Create nodes with specified drift
    nodes = [DriftingNode(f"node_{i}", drift_factors[i]) for i in range(num_nodes)]

    # Connect all nodes in a mesh network
    for i in range(num_nodes):
        for j in range(i + 1, num_nodes):
            nodes[i].connect(nodes[j])

    # Perform updates
    start_time = time.time()
    update_count = 0
    inconsistency_count = 0

    # Perform updates in rounds to observe consistency over time
    for round_idx in range(5):
        update_tasks = []

        # Each node updates some keys
        updates_per_node = num_updates // (5 * num_nodes)
        for node_idx, node in enumerate(nodes):
            for i in range(updates_per_node):
                key = f"key_{round_idx}_{i}"
                value = f"value_from_{node.node_id}_round_{round_idx}_{i}"
                update_tasks.append(node.set_value(key, value))
                update_count += 1

        # Execute all updates for this round
        await asyncio.gather(*update_tasks)

        # Allow some time for propagation
        await asyncio.sleep(0.2)

        # Check consistency after this round
        round_inconsistencies = 0
        for i in range(updates_per_node):
            for round_idx in range(round_idx + 1):  # Check all keys up to current round
                key = f"key_{round_idx}_{i}"
                values = []

                for node in nodes:
                    value = await node.get_value(key)
                    values.append(value)

                # Check if all nodes have the same value
                unique_values = set(v for v in values if v is not None)
                if len(unique_values) > 1:
                    round_inconsistencies += 1
                    logger.warning(f"Inconsistency for {key}: {values}")

        inconsistency_count += round_inconsistencies
        logger.info(
            f"Round {round_idx} completed. Inconsistencies: {round_inconsistencies}"
        )

    total_time = time.time() - start_time
    consistency_rate = (
        (1 - inconsistency_count / update_count) * 100 if update_count > 0 else 0
    )

    logger.info(f"Test completed in {total_time:.2f}s")
    logger.info(f"Consistency rate: {consistency_rate:.2f}%")
    logger.info(f"Inconsistencies: {inconsistency_count}/{update_count}")

    # Analyze final state to see which node's updates won most frequently
    win_count = {node.node_id: 0 for node in nodes}
    total_keys = 0

    for round_idx in range(5):
        updates_per_node = num_updates // (5 * num_nodes)
        for i in range(updates_per_node):
            key = f"key_{round_idx}_{i}"

            # Get the final value on the first node
            final_value = await nodes[0].get_value(key)
            if final_value is not None:
                total_keys += 1

                # Determine which node's update won
                for node in nodes:
                    if f"value_from_{node.node_id}" in final_value:
                        win_count[node.node_id] += 1
                        break

    logger.info("Final state analysis:")
    for node_id, wins in win_count.items():
        if total_keys > 0:
            win_percentage = (wins / total_keys) * 100
            logger.info(
                f"  {node_id}: {wins}/{total_keys} wins ({win_percentage:.1f}%)"
            )

    return {
        "total_time": total_time,
        "consistency_rate": consistency_rate,
        "inconsistency_count": inconsistency_count,
        "update_count": update_count,
        "win_count": win_count,
        "total_keys": total_keys,
    }


async def main():
    """Run the test suite with various clock drift configurations"""
    logger.info("Starting clock drift test suite")

    # Test configurations
    configs = [
        {"name": "Mild drift", "factors": [1.0, 1.1, 0.9, 1.0]},
        {"name": "Moderate drift", "factors": [1.0, 1.5, 0.7, 1.0]},
        {"name": "Severe drift", "factors": [1.0, 3.0, 0.3, 1.0]},
    ]

    for config in configs:
        logger.info(f"\n--- Test: {config['name']} ---")
        result = await run_clock_drift_test(4, 100, config["factors"])

        print(f"Results for {config['name']}:")
        print(f"  - Consistency Rate: {result['consistency_rate']:.2f}%")
        print(f"  - Total Time: {result['total_time']:.2f}s")
        print(
            f"  - Inconsistencies: {result['inconsistency_count']}/{result['update_count']}"
        )

        # Show which nodes won most frequently
        print("  - Update winner distribution:")
        for node_id, wins in result["win_count"].items():
            if result["total_keys"] > 0:
                win_percentage = (wins / result["total_keys"]) * 100
                drift_factor = config["factors"][int(node_id.split("_")[1])]
                print(f"    {node_id} (drift={drift_factor}): {win_percentage:.1f}%")
        print()


if __name__ == "__main__":
    asyncio.run(main())
