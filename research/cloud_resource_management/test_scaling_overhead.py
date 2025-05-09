#!/usr/bin/env python3
"""
Test Case: Scalability Testing
Objective: Determine management scalability limits
"""

import asyncio
import logging
import statistics
import sys
import time
from pathlib import Path
from typing import List

import psutil  # type: ignore

# Add project root to path so we can import HORAO modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from horao.controllers.base import ResourceController

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ResourceManager:
    """Resource manager for testing scalability"""

    def __init__(self):
        self.controller = ResourceController("test-controller")
        self.resources = {}

    async def create_resources(
        self, count: int, resource_type: str = "vm", batch_size: int = 10
    ):
        """
        Create a specified number of resources

        Args:
            count: Number of resources to create
            resource_type: Type of resources to create
            batch_size: Number of resources to create in each batch
        """
        start_time = time.time()
        created = 0

        # Create resources in batches to limit concurrency
        for batch_start in range(0, count, batch_size):
            batch_end = min(batch_start + batch_size, count)
            batch_size = batch_end - batch_start

            logger.info(
                f"Creating batch of {batch_size} resources ({batch_start+1}-{batch_end}/{count})"
            )

            tasks = []
            for i in range(batch_start, batch_end):
                name = f"{resource_type}-{i+1}"
                config = {"name": name, "size": "small"}

                if resource_type == "vm":
                    tasks.append(self.controller.provision_resource("vm", config))
                elif resource_type == "storage":
                    tasks.append(self.controller.provision_resource("storage", config))
                elif resource_type == "network":
                    tasks.append(self.controller.provision_resource("network", config))

            # Wait for the batch to complete
            batch_results = await asyncio.gather(*tasks)
            created += len(batch_results)

            for resource_id in batch_results:
                self.resources[resource_id] = await self.controller.get_resource(
                    resource_id
                )

            # Calculate progress
            elapsed = time.time() - start_time
            resources_per_second = created / elapsed if elapsed > 0 else 0
            estimated_remaining = (
                (count - created) / resources_per_second
                if resources_per_second > 0
                else 0
            )

            logger.info(
                f"Progress: {created}/{count} resources created "
                f"({resources_per_second:.2f} resources/sec, "
                f"~{estimated_remaining:.1f}s remaining)"
            )

        total_time = time.time() - start_time
        resources_per_second = count / total_time if total_time > 0 else 0

        logger.info(
            f"Created {count} resources in {total_time:.2f}s ({resources_per_second:.2f} resources/sec)"
        )

        return {
            "count": count,
            "total_time": total_time,
            "resources_per_second": resources_per_second,
        }

    async def list_resources(self, count: int = None):
        """
        List and process resources to measure management plane performance

        Args:
            count: Number of resources to list (None for all)
        """
        start_time = time.time()

        # Get all resources
        resources = await self.controller.get_resources()

        if count is not None:
            resource_ids = list(resources.keys())[:count]
            resources = {rid: resources[rid] for rid in resource_ids}

        # Simulate processing each resource (calculating statistics, etc.)
        result_data = []
        for resource_id, resource in resources.items():
            # Simulate lightweight processing
            await asyncio.sleep(0.001)
            result_data.append(
                {
                    "id": resource_id,
                    "type": resource["type"],
                    "status": resource["status"],
                }
            )

        total_time = time.time() - start_time
        resources_per_second = len(resources) / total_time if total_time > 0 else 0

        logger.info(
            f"Listed and processed {len(resources)} resources in {total_time:.2f}s "
            f"({resources_per_second:.2f} resources/sec)"
        )

        return {
            "count": len(resources),
            "total_time": total_time,
            "resources_per_second": resources_per_second,
        }


async def measure_system_resources(interval: float = 0.1, duration: float = 10.0):
    """
    Measure system resources (CPU, memory) at specified intervals

    Args:
        interval: Measurement interval in seconds
        duration: Total measurement duration in seconds

    Returns:
        Dictionary with resource usage statistics
    """
    measurements = []
    start_time = time.time()

    while time.time() - start_time < duration:
        cpu_percent = psutil.cpu_percent(interval=None)
        memory_info = psutil.virtual_memory()

        measurements.append(
            {
                "timestamp": time.time() - start_time,
                "cpu_percent": cpu_percent,
                "memory_percent": memory_info.percent,
                "memory_used_mb": memory_info.used / (1024 * 1024),
            }
        )

        await asyncio.sleep(interval)

    # Calculate statistics
    cpu_values = [m["cpu_percent"] for m in measurements]
    memory_percent_values = [m["memory_percent"] for m in measurements]
    memory_mb_values = [m["memory_used_mb"] for m in measurements]

    stats = {
        "cpu_percent": {
            "min": min(cpu_values),
            "max": max(cpu_values),
            "mean": statistics.mean(cpu_values),
            "median": statistics.median(cpu_values),
        },
        "memory_percent": {
            "min": min(memory_percent_values),
            "max": max(memory_percent_values),
            "mean": statistics.mean(memory_percent_values),
            "median": statistics.median(memory_percent_values),
        },
        "memory_used_mb": {
            "min": min(memory_mb_values),
            "max": max(memory_mb_values),
            "mean": statistics.mean(memory_mb_values),
            "median": statistics.median(memory_mb_values),
        },
        "measurements": measurements,
    }

    return stats


async def run_scalability_test(resource_counts: List[int], resource_type: str = "vm"):
    """
    Run scalability test with different resource counts

    Args:
        resource_counts: List of resource counts to test
        resource_type: Type of resources to create
    """
    manager = ResourceManager()
    results = {}

    for count in resource_counts:
        logger.info(f"\n=== Testing with {count} {resource_type}s ===")

        # Start resource monitoring in background
        monitoring_task = asyncio.create_task(
            measure_system_resources(interval=0.5, duration=120)
        )

        # Create resources
        creation_result = await manager.create_resources(count, resource_type)

        # List resources to test management plane performance
        list_result = await manager.list_resources()

        # Wait for monitoring to complete
        resource_usage = await monitoring_task

        results[count] = {
            "creation": creation_result,
            "listing": list_result,
            "resource_usage": resource_usage,
        }

        logger.info(f"Completed test with {count} {resource_type}s\n")

    return results


async def main():
    """Run the scalability test suite"""
    logger.info("Starting scalability test suite")

    # Resource counts to test
    # In a real test, use larger values like [10, 50, 100, 500, 1000]
    # Using smaller values here for quick testing
    resource_counts = [10, 50, 100]

    # Run tests with VMs
    results = await run_scalability_test(resource_counts, "vm")

    # Print summary
    print("\nScalability Test Results Summary:")
    print("=========================================")

    for count, data in results.items():
        creation = data["creation"]
        listing = data["listing"]
        resource = data["resource_usage"]

        print(f"\nResults for {count} VMs:")
        print(
            f"  Creation: {creation['total_time']:.2f}s ({creation['resources_per_second']:.2f} VMs/sec)"
        )
        print(
            f"  Listing: {listing['total_time']:.2f}s ({listing['resources_per_second']:.2f} VMs/sec)"
        )
        print(
            f"  CPU Usage: {resource['cpu_percent']['mean']:.1f}% (peak: {resource['cpu_percent']['max']:.1f}%)"
        )
        print(
            f"  Memory Usage: {resource['memory_used_mb']['mean']:.1f}MB (peak: {resource['memory_used_mb']['max']:.1f}MB)"
        )

    # Analyze scaling characteristics
    print("\nScaling Characteristics:")

    # Calculate how performance scales with resource count
    if len(resource_counts) >= 2:
        smallest_count = min(resource_counts)
        largest_count = max(resource_counts)

        smallest_creation_rate = results[smallest_count]["creation"][
            "resources_per_second"
        ]
        largest_creation_rate = results[largest_count]["creation"][
            "resources_per_second"
        ]

        smallest_listing_rate = results[smallest_count]["listing"][
            "resources_per_second"
        ]
        largest_listing_rate = results[largest_count]["listing"]["resources_per_second"]

        # Calculate scaling factors
        creation_scaling = (
            largest_creation_rate / smallest_creation_rate
            if smallest_creation_rate > 0
            else 0
        )
        listing_scaling = (
            largest_listing_rate / smallest_listing_rate
            if smallest_listing_rate > 0
            else 0
        )
        count_scaling = largest_count / smallest_count

        # Ideal scaling would maintain the same rate regardless of count (scaling factor = 1.0)
        print(f"  Creation performance scaling: {creation_scaling:.2f}x (ideal: 1.0x)")
        print(f"  Listing performance scaling: {listing_scaling:.2f}x (ideal: 1.0x)")

        if creation_scaling < 0.8:
            print("  Creation performance deteriorates as resource count increases")
        elif creation_scaling > 1.2:
            print(
                "  Creation performance improves as resource count increases (batch efficiency)"
            )
        else:
            print("  Creation performance scales well with resource count")

        if listing_scaling < 0.5:
            print(
                "  Listing performance significantly deteriorates as resource count increases"
            )
        elif listing_scaling < 0.8:
            print(
                "  Listing performance moderately deteriorates as resource count increases"
            )
        else:
            print("  Listing performance scales well with resource count")


if __name__ == "__main__":
    # Check if psutil is available, and if not, provide instructions
    try:
        import psutil  # type: ignore
    except ImportError:
        print("The 'psutil' package is required for this test.")
        print("Please install it using: pip install psutil")
        sys.exit(1)

    asyncio.run(main())
