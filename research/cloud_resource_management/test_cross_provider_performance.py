#!/usr/bin/env python3
"""
Test Case: Cross-Provider Resource Provisioning
Objective: Measure provisioning performance across different cloud providers
"""

import asyncio
import logging
import statistics
import sys
import time
from pathlib import Path
from typing import Dict, List

# Add project root to path so we can import HORAO modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from horao.controllers.aws import AWSController
from horao.controllers.gcp import GCPController
from horao.physical.computer import VirtualMachine

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ProviderBenchmark:
    """Benchmark harness for cloud provider performance testing"""

    def __init__(self):
        # Initialize controllers for different providers
        self.controllers = {
            "aws": AWSController(),
            "gcp": GCPController(),
            # Add more providers here
        }

    async def benchmark_vm_provisioning(
        self, provider: str, vm_config: Dict, count: int = 1
    ) -> Dict:
        """
        Benchmark VM provisioning for a specific provider

        Args:
            provider: Cloud provider name
            vm_config: VM configuration
            count: Number of VMs to provision

        Returns:
            Dictionary with benchmark results
        """
        if provider not in self.controllers:
            raise ValueError(f"Provider {provider} not supported")

        controller = self.controllers[provider]
        results = []

        logger.info(
            f"Benchmarking {provider}: Provisioning {count} VMs with config: {vm_config}"
        )

        # Create VM instances
        vms = []
        for i in range(count):
            vm = VirtualMachine(
                name=f"{provider}-vm-{i}",
                size=vm_config.get("size", "small"),
                provider=provider,
            )
            vms.append(vm)

        # Measure provisioning time for each VM
        start_time = time.time()

        tasks = []
        for vm in vms:
            tasks.append(controller.provision_resource("vm", vm_config))

        # Wait for all VMs to be provisioned
        vm_results = await asyncio.gather(*tasks)

        # Record individual provision times
        provision_times = [result["provision_time"] for result in vm_results]

        total_time = time.time() - start_time

        # Calculate statistics
        stats = {
            "provider": provider,
            "vm_count": count,
            "total_time": total_time,
            "average_time": statistics.mean(provision_times) if provision_times else 0,
            "min_time": min(provision_times) if provision_times else 0,
            "max_time": max(provision_times) if provision_times else 0,
            "median_time": statistics.median(provision_times) if provision_times else 0,
        }

        logger.info(f"Benchmark results for {provider}: {stats}")
        return stats

    async def run_cross_provider_benchmark(
        self, vm_configs: Dict[str, Dict], counts: List[int]
    ) -> Dict:
        """
        Run benchmarks across all providers

        Args:
            vm_configs: Dictionary mapping provider names to VM configs
            counts: List of VM counts to test

        Returns:
            Dictionary with benchmark results for all providers
        """
        results = {}

        for provider, config in vm_configs.items():
            provider_results = {}

            for count in counts:
                try:
                    result = await self.benchmark_vm_provisioning(
                        provider, config, count
                    )
                    provider_results[count] = result
                except Exception as e:
                    logger.error(f"Error benchmarking {provider} with {count} VMs: {e}")
                    provider_results[count] = {"error": str(e)}

            results[provider] = provider_results

        return results

    def analyze_results(self, results: Dict) -> Dict:
        """
        Analyze benchmark results to generate insights

        Args:
            results: Dictionary with benchmark results

        Returns:
            Dictionary with analysis
        """
        analysis = {}

        # Compare providers
        for count in next(iter(results.values())).keys():
            providers_at_count = {}

            for provider, provider_results in results.items():
                if count in provider_results and "error" not in provider_results[count]:
                    providers_at_count[provider] = provider_results[count]

            if len(providers_at_count) > 1:
                # Find fastest provider
                fastest = min(
                    providers_at_count.items(), key=lambda x: x[1]["average_time"]
                )

                # Calculate relative performance
                relative_perf = {}
                for provider, data in providers_at_count.items():
                    relative_perf[provider] = (
                        fastest[1]["average_time"] / data["average_time"]
                    )

                analysis[count] = {
                    "fastest_provider": fastest[0],
                    "fastest_time": fastest[1]["average_time"],
                    "relative_performance": relative_perf,
                }

        return analysis


async def main():
    """Run the benchmark suite"""
    logger.info("Starting cross-provider benchmark")

    benchmark = ProviderBenchmark()

    # Define VM configurations for different providers
    vm_configs = {
        "aws": {"size": "t3.medium", "region": "us-west-2"},
        "gcp": {"size": "n2-standard-2", "region": "us-central1"},
    }

    # VM counts to test
    counts = [1, 5, 10]

    # Run benchmarks
    results = await benchmark.run_cross_provider_benchmark(vm_configs, counts)

    # Analyze results
    analysis = benchmark.analyze_results(results)

    # Print summary
    print("\nCross-Provider Benchmark Results Summary:")
    print("=========================================")

    for count in counts:
        print(f"\nResults for {count} VMs:")
        for provider, provider_results in results.items():
            if count in provider_results and "error" not in provider_results[count]:
                res = provider_results[count]
                print(
                    f"  {provider.upper()}: Avg={res['average_time']:.2f}s, Min={res['min_time']:.2f}s, Max={res['max_time']:.2f}s"
                )

        if count in analysis:
            print(
                f"  Fastest: {analysis[count]['fastest_provider'].upper()} ({analysis[count]['fastest_time']:.2f}s)"
            )
            print("  Relative Performance (higher is better):")
            for provider, rel_perf in analysis[count]["relative_performance"].items():
                print(f"    {provider.upper()}: {rel_perf:.2f}x")


if __name__ == "__main__":
    asyncio.run(main())
