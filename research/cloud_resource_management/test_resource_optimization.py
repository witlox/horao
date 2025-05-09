#!/usr/bin/env python3
"""
Test Case: Resource Optimization Algorithm Testing
Objective: Evaluate resource allocation optimization algorithms
"""

import asyncio
import json
import logging
import random
import sys
import time
from pathlib import Path
from typing import Dict, List

# Add project root to path so we can import HORAO modules
sys.path.append(str(Path(__file__).parent.parent.parent))


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CloudProvider:
    """Mock cloud provider for optimization testing"""

    def __init__(
        self,
        name: str,
        regions: List[str],
        vm_types: List[Dict],
        pricing_factor: float = 1.0,
        latency_factor: float = 1.0,
    ):
        """
        Initialize a cloud provider model

        Args:
            name: Provider name (aws, gcp, azure)
            regions: List of region names
            vm_types: List of VM type dictionaries with specs
            pricing_factor: Relative pricing factor (1.0 = standard)
            latency_factor: Relative latency factor (1.0 = standard)
        """
        self.name = name
        self.regions = regions
        self.vm_types = vm_types
        self.pricing_factor = pricing_factor
        self.latency_factor = latency_factor

    def get_vm_price(self, vm_type: str, region: str) -> float:
        """Get hourly price for a VM type in a region"""
        base_price = next(
            (vm["price"] for vm in self.vm_types if vm["name"] == vm_type), 0
        )

        # Apply regional price variation (some regions are more expensive)
        region_index = self.regions.index(region) if region in self.regions else 0
        region_factor = 1.0 + (region_index % 3) * 0.1  # 10% increments

        return base_price * self.pricing_factor * region_factor

    def get_vm_specs(self, vm_type: str) -> Dict:
        """Get specifications for a VM type"""
        specs = next((vm.copy() for vm in self.vm_types if vm["name"] == vm_type), {})
        if "price" in specs:
            del specs["price"]  # Price depends on region
        return specs

    def estimate_latency(self, region: str, target_location: str) -> float:
        """Estimate network latency between region and target location in ms"""
        # Simple model: latency increases with "distance" between regions
        # Distance approximated by difference in region name indices
        if region not in self.regions:
            return 200.0  # Default high latency

        region_index = self.regions.index(region)
        target_index = sum(ord(c) for c in target_location) % 10  # Hash target to 0-9
        distance = abs(region_index - target_index)

        # Base latency: 10ms + distance factor + provider-specific factor
        return (10.0 + distance * 15.0) * self.latency_factor


class WorkloadProfile:
    """Represents a workload with resource requirements"""

    def __init__(
        self,
        name: str,
        cpu_needed: float,
        memory_needed: float,
        storage_needed: float,
        latency_sensitive: bool = False,
        location_constraint: str = None,
    ):
        """
        Initialize a workload profile

        Args:
            name: Workload name
            cpu_needed: CPU cores needed
            memory_needed: Memory needed in GB
            storage_needed: Storage needed in GB
            latency_sensitive: Whether workload is sensitive to network latency
            location_constraint: Preferred geographic location (if any)
        """
        self.name = name
        self.cpu_needed = cpu_needed
        self.memory_needed = memory_needed
        self.storage_needed = storage_needed
        self.latency_sensitive = latency_sensitive
        self.location_constraint = location_constraint


class OptimizationAlgorithm:
    """Base class for resource allocation optimization algorithms"""

    def __init__(self, name: str, providers: List[CloudProvider]):
        """
        Initialize optimization algorithm

        Args:
            name: Algorithm name
            providers: List of available cloud providers
        """
        self.name = name
        self.providers = providers

    def optimize(self, workloads: List[WorkloadProfile]) -> Dict:
        """
        Optimize resource allocation for workloads

        Args:
            workloads: List of workload profiles to allocate

        Returns:
            Dictionary with allocation decisions and metrics
        """
        raise NotImplementedError("Optimization algorithm not implemented")


class CostOptimizationAlgorithm(OptimizationAlgorithm):
    """Optimizes resource allocation primarily for cost"""

    def __init__(self, providers: List[CloudProvider]):
        super().__init__("cost_optimization", providers)

    def optimize(self, workloads: List[WorkloadProfile]) -> Dict:
        """Optimize for lowest total cost"""
        allocation = {}
        total_cost = 0.0

        for workload in workloads:
            best_cost = float("inf")
            best_allocation = None

            # Try all provider/region/vm-type combinations
            for provider in self.providers:
                for region in provider.regions:
                    for vm_type in provider.vm_types:
                        # Check if VM meets requirements
                        if (
                            vm_type["cpu"] >= workload.cpu_needed
                            and vm_type["memory"] >= workload.memory_needed
                            and vm_type["storage"] >= workload.storage_needed
                        ):

                            # Calculate cost
                            cost = provider.get_vm_price(vm_type["name"], region)

                            # If this is cheaper than previous best
                            if cost < best_cost:
                                best_cost = cost
                                best_allocation = {
                                    "provider": provider.name,
                                    "region": region,
                                    "vm_type": vm_type["name"],
                                    "hourly_cost": cost,
                                }

            if best_allocation:
                allocation[workload.name] = best_allocation
                total_cost += best_cost

        return {
            "algorithm": self.name,
            "allocation": allocation,
            "total_hourly_cost": total_cost,
            "allocation_success_rate": (
                len(allocation) / len(workloads) if workloads else 1.0
            ),
        }


class LatencyOptimizationAlgorithm(OptimizationAlgorithm):
    """Optimizes resource allocation primarily for network latency"""

    def __init__(self, providers: List[CloudProvider]):
        super().__init__("latency_optimization", providers)

    def optimize(self, workloads: List[WorkloadProfile]) -> Dict:
        """Optimize for lowest network latency"""
        allocation = {}
        total_cost = 0.0
        average_latency = 0.0

        for workload in workloads:
            best_latency = float("inf")
            best_allocation = None

            # Try all provider/region/vm-type combinations
            for provider in self.providers:
                for region in provider.regions:
                    # Estimate latency to workload's preferred location
                    latency = provider.estimate_latency(
                        region, workload.location_constraint or "default"
                    )

                    for vm_type in provider.vm_types:
                        # Check if VM meets requirements
                        if (
                            vm_type["cpu"] >= workload.cpu_needed
                            and vm_type["memory"] >= workload.memory_needed
                            and vm_type["storage"] >= workload.storage_needed
                        ):

                            # Calculate cost
                            cost = provider.get_vm_price(vm_type["name"], region)

                            # If this has better latency than previous best
                            if latency < best_latency:
                                best_latency = latency
                                best_allocation = {
                                    "provider": provider.name,
                                    "region": region,
                                    "vm_type": vm_type["name"],
                                    "hourly_cost": cost,
                                    "estimated_latency_ms": latency,
                                }

            if best_allocation:
                allocation[workload.name] = best_allocation
                total_cost += best_allocation["hourly_cost"]
                average_latency += best_allocation["estimated_latency_ms"]

        if allocation:
            average_latency /= len(allocation)

        return {
            "algorithm": self.name,
            "allocation": allocation,
            "total_hourly_cost": total_cost,
            "average_latency_ms": average_latency,
            "allocation_success_rate": (
                len(allocation) / len(workloads) if workloads else 1.0
            ),
        }


class HybridOptimizationAlgorithm(OptimizationAlgorithm):
    """Optimizes resource allocation balancing cost and latency"""

    def __init__(
        self,
        providers: List[CloudProvider],
        cost_weight: float = 0.5,
        latency_weight: float = 0.5,
    ):
        """
        Initialize hybrid optimization algorithm

        Args:
            providers: List of available cloud providers
            cost_weight: Weight for cost factor (0.0-1.0)
            latency_weight: Weight for latency factor (0.0-1.0)
        """
        super().__init__("hybrid_optimization", providers)
        # Normalize weights
        total_weight = cost_weight + latency_weight
        self.cost_weight = cost_weight / total_weight
        self.latency_weight = latency_weight / total_weight

    def optimize(self, workloads: List[WorkloadProfile]) -> Dict:
        """Optimize for balanced cost and latency"""
        allocation = {}
        total_cost = 0.0
        average_latency = 0.0

        # Find min/max costs and latencies for normalization
        min_cost = float("inf")
        max_cost = 0.0
        min_latency = float("inf")
        max_latency = 0.0

        for provider in self.providers:
            for region in provider.regions:
                for vm_type in provider.vm_types:
                    cost = provider.get_vm_price(vm_type["name"], region)
                    min_cost = min(min_cost, cost)
                    max_cost = max(max_cost, cost)

                    latency = provider.estimate_latency(region, "default")
                    min_latency = min(min_latency, latency)
                    max_latency = max(max_latency, latency)

        # Avoid division by zero
        cost_range = max_cost - min_cost
        if cost_range == 0:
            cost_range = 1
        latency_range = max_latency - min_latency
        if latency_range == 0:
            latency_range = 1

        for workload in workloads:
            best_score = float("inf")  # Lower is better
            best_allocation = None

            # Adjust weights based on workload sensitivity
            effective_cost_weight = self.cost_weight
            effective_latency_weight = self.latency_weight

            if workload.latency_sensitive:
                # Increase latency weight for sensitive workloads
                effective_latency_weight *= 2
                total = effective_cost_weight + effective_latency_weight
                effective_cost_weight /= total
                effective_latency_weight /= total

            # Try all provider/region/vm-type combinations
            for provider in self.providers:
                for region in provider.regions:
                    # Estimate latency to workload's preferred location
                    latency = provider.estimate_latency(
                        region, workload.location_constraint or "default"
                    )

                    for vm_type in provider.vm_types:
                        # Check if VM meets requirements
                        if (
                            vm_type["cpu"] >= workload.cpu_needed
                            and vm_type["memory"] >= workload.memory_needed
                            and vm_type["storage"] >= workload.storage_needed
                        ):

                            # Calculate cost
                            cost = provider.get_vm_price(vm_type["name"], region)

                            # Normalize cost and latency to 0-1 scale
                            normalized_cost = (cost - min_cost) / cost_range
                            normalized_latency = (latency - min_latency) / latency_range

                            # Compute weighted score (lower is better)
                            score = (
                                normalized_cost * effective_cost_weight
                                + normalized_latency * effective_latency_weight
                            )

                            # If this has better score than previous best
                            if score < best_score:
                                best_score = score
                                best_allocation = {
                                    "provider": provider.name,
                                    "region": region,
                                    "vm_type": vm_type["name"],
                                    "hourly_cost": cost,
                                    "estimated_latency_ms": latency,
                                    "score": score,
                                }

            if best_allocation:
                allocation[workload.name] = best_allocation
                total_cost += best_allocation["hourly_cost"]
                average_latency += best_allocation["estimated_latency_ms"]

        if allocation:
            average_latency /= len(allocation)

        return {
            "algorithm": self.name,
            "allocation": allocation,
            "total_hourly_cost": total_cost,
            "average_latency_ms": average_latency,
            "allocation_success_rate": (
                len(allocation) / len(workloads) if workloads else 1.0
            ),
        }


class OptimizationBenchmark:
    """Benchmark for evaluating resource allocation algorithms"""

    def __init__(self):
        """Initialize benchmark with cloud providers and workloads"""
        # Create mock cloud providers
        self.providers = [
            CloudProvider(
                name="aws",
                regions=["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
                vm_types=[
                    {
                        "name": "t3.micro",
                        "cpu": 2,
                        "memory": 1,
                        "storage": 20,
                        "price": 0.0104,
                    },
                    {
                        "name": "t3.small",
                        "cpu": 2,
                        "memory": 2,
                        "storage": 20,
                        "price": 0.0208,
                    },
                    {
                        "name": "m5.large",
                        "cpu": 2,
                        "memory": 8,
                        "storage": 50,
                        "price": 0.096,
                    },
                    {
                        "name": "c5.large",
                        "cpu": 2,
                        "memory": 4,
                        "storage": 40,
                        "price": 0.085,
                    },
                    {
                        "name": "r5.large",
                        "cpu": 2,
                        "memory": 16,
                        "storage": 50,
                        "price": 0.126,
                    },
                ],
                pricing_factor=1.0,
                latency_factor=1.0,
            ),
            CloudProvider(
                name="gcp",
                regions=["us-central1", "us-east4", "europe-west1", "asia-east1"],
                vm_types=[
                    {
                        "name": "e2-micro",
                        "cpu": 2,
                        "memory": 1,
                        "storage": 20,
                        "price": 0.0094,
                    },
                    {
                        "name": "e2-small",
                        "cpu": 2,
                        "memory": 2,
                        "storage": 20,
                        "price": 0.0188,
                    },
                    {
                        "name": "n2-standard-2",
                        "cpu": 2,
                        "memory": 8,
                        "storage": 50,
                        "price": 0.094,
                    },
                    {
                        "name": "c2-standard-4",
                        "cpu": 4,
                        "memory": 16,
                        "storage": 40,
                        "price": 0.2088,
                    },
                    {
                        "name": "m1-megamem-96",
                        "cpu": 96,
                        "memory": 1433.6,
                        "storage": 300,
                        "price": 10.6740,
                    },
                ],
                pricing_factor=0.95,  # 5% cheaper than AWS
                latency_factor=1.05,  # 5% higher latency than AWS
            ),
            CloudProvider(
                name="azure",
                regions=["eastus", "westus2", "westeurope", "southeastasia"],
                vm_types=[
                    {
                        "name": "B1s",
                        "cpu": 1,
                        "memory": 1,
                        "storage": 20,
                        "price": 0.0114,
                    },
                    {
                        "name": "B2s",
                        "cpu": 2,
                        "memory": 4,
                        "storage": 40,
                        "price": 0.0456,
                    },
                    {
                        "name": "D2s_v3",
                        "cpu": 2,
                        "memory": 8,
                        "storage": 50,
                        "price": 0.099,
                    },
                    {
                        "name": "F2s_v2",
                        "cpu": 2,
                        "memory": 4,
                        "storage": 40,
                        "price": 0.087,
                    },
                    {
                        "name": "E2s_v3",
                        "cpu": 2,
                        "memory": 16,
                        "storage": 50,
                        "price": 0.1296,
                    },
                ],
                pricing_factor=1.02,  # 2% more expensive than AWS
                latency_factor=0.98,  # 2% lower latency than AWS
            ),
        ]

        # Create optimization algorithms
        self.algorithms = [
            CostOptimizationAlgorithm(self.providers),
            LatencyOptimizationAlgorithm(self.providers),
            HybridOptimizationAlgorithm(self.providers, 0.5, 0.5),  # Balanced
            HybridOptimizationAlgorithm(self.providers, 0.7, 0.3),  # Cost-focused
            HybridOptimizationAlgorithm(self.providers, 0.3, 0.7),  # Latency-focused
        ]

    def generate_workloads(self, count: int) -> List[WorkloadProfile]:
        """Generate random workload profiles for testing"""
        workloads = []

        # Define some realistic workload templates
        templates = [
            {
                "name_prefix": "web",
                "cpu_range": (1, 4),
                "memory_range": (1, 8),
                "storage_range": (10, 50),
                "latency_sensitive_prob": 0.7,
            },
            {
                "name_prefix": "batch",
                "cpu_range": (4, 16),
                "memory_range": (16, 64),
                "storage_range": (50, 200),
                "latency_sensitive_prob": 0.1,
            },
            {
                "name_prefix": "db",
                "cpu_range": (2, 8),
                "memory_range": (8, 32),
                "storage_range": (100, 500),
                "latency_sensitive_prob": 0.5,
            },
            {
                "name_prefix": "ml",
                "cpu_range": (8, 32),
                "memory_range": (32, 128),
                "storage_range": (200, 1000),
                "latency_sensitive_prob": 0.3,
            },
        ]

        # Locations for distribution
        locations = ["us", "europe", "asia", "australia"]

        # Generate workloads
        for i in range(count):
            template = random.choice(templates)

            workload = WorkloadProfile(
                name=f"{template['name_prefix']}-{i+1}",
                cpu_needed=random.uniform(*template["cpu_range"]),
                memory_needed=random.uniform(*template["memory_range"]),
                storage_needed=random.uniform(*template["storage_range"]),
                latency_sensitive=random.random() < template["latency_sensitive_prob"],
                location_constraint=random.choice(locations),
            )

            workloads.append(workload)

        return workloads

    def run_benchmark(self, workload_counts: List[int]) -> Dict:
        """
        Run benchmark with different workload sizes

        Args:
            workload_counts: List of workload counts to test

        Returns:
            Dictionary with benchmark results
        """
        results = {}

        for count in workload_counts:
            logger.info(f"Running benchmark with {count} workloads")

            # Generate workloads
            workloads = self.generate_workloads(count)

            # Run each algorithm
            algorithm_results = {}

            for algorithm in self.algorithms:
                logger.info(f"Running {algorithm.name} algorithm")

                start_time = time.time()
                result = algorithm.optimize(workloads)
                elapsed_time = time.time() - start_time

                result["execution_time"] = elapsed_time
                algorithm_results[algorithm.name] = result

            results[count] = algorithm_results

        return results

    def analyze_results(self, results: Dict) -> Dict:
        """
        Analyze benchmark results

        Args:
            results: Dictionary with benchmark results

        Returns:
            Dictionary with analysis
        """
        analysis = {}

        # For each workload count
        for count, count_results in results.items():
            count_analysis = {
                "cost_comparison": {},
                "latency_comparison": {},
                "execution_time_comparison": {},
                "allocation_success_comparison": {},
            }

            # Get baseline metrics from cost optimization algorithm
            baseline = count_results.get("cost_optimization", {})
            baseline_cost = baseline.get("total_hourly_cost", 0)

            if "latency_optimization" in count_results:
                baseline_latency = count_results["latency_optimization"].get(
                    "average_latency_ms", 0
                )
            else:
                baseline_latency = 0

            # Compare metrics across algorithms
            for algo_name, algo_result in count_results.items():
                # Cost comparison (relative to cost optimization algorithm)
                if baseline_cost > 0:
                    relative_cost = (
                        algo_result.get("total_hourly_cost", 0) / baseline_cost
                    )
                    count_analysis["cost_comparison"][algo_name] = relative_cost

                # Latency comparison (relative to latency optimization algorithm)
                if baseline_latency > 0:
                    relative_latency = (
                        algo_result.get("average_latency_ms", 0) / baseline_latency
                    )
                    count_analysis["latency_comparison"][algo_name] = relative_latency

                # Execution time
                count_analysis["execution_time_comparison"][algo_name] = (
                    algo_result.get("execution_time", 0)
                )

                # Allocation success rate
                count_analysis["allocation_success_comparison"][algo_name] = (
                    algo_result.get("allocation_success_rate", 0)
                )

            analysis[count] = count_analysis

        return analysis

    def plot_results(self, results: Dict, analysis: Dict, output_dir: str = "."):
        """
        Create plots to visualize benchmark results

        Args:
            results: Benchmark results
            analysis: Analysis of results
            output_dir: Directory to save plots
        """
        try:
            from pathlib import Path

            import matplotlib.pyplot as plt  # type: ignore
            import numpy as np  # type: ignore

            # Create output directory if it doesn't exist
            Path(output_dir).mkdir(exist_ok=True)

            # Extract workload counts
            counts = sorted(list(results.keys()))

            # Cost comparison plot
            plt.figure(figsize=(10, 6))
            for algo_name in self.algorithms[0:5]:  # First 5 algorithms
                values = [
                    analysis[count]["cost_comparison"].get(algo_name.name, float("nan"))
                    for count in counts
                ]
                plt.plot(counts, values, marker="o", label=algo_name.name)

            plt.title("Cost Comparison (Relative to Cost Optimization)")
            plt.xlabel("Workload Count")
            plt.ylabel("Relative Cost (lower is better)")
            plt.grid(True, linestyle="--", alpha=0.7)
            plt.legend()
            plt.tight_layout()
            plt.savefig(f"{output_dir}/cost_comparison.png")

            # Latency comparison plot
            plt.figure(figsize=(10, 6))
            for algo_name in self.algorithms[0:5]:  # First 5 algorithms
                values = [
                    analysis[count]["latency_comparison"].get(
                        algo_name.name, float("nan")
                    )
                    for count in counts
                ]
                plt.plot(counts, values, marker="o", label=algo_name.name)

            plt.title("Latency Comparison (Relative to Latency Optimization)")
            plt.xlabel("Workload Count")
            plt.ylabel("Relative Latency (lower is better)")
            plt.grid(True, linestyle="--", alpha=0.7)
            plt.legend()
            plt.tight_layout()
            plt.savefig(f"{output_dir}/latency_comparison.png")

            # Execution time plot
            plt.figure(figsize=(10, 6))
            for algo_name in self.algorithms[0:5]:  # First 5 algorithms
                values = [
                    analysis[count]["execution_time_comparison"].get(
                        algo_name.name, float("nan")
                    )
                    for count in counts
                ]
                plt.plot(counts, values, marker="o", label=algo_name.name)

            plt.title("Execution Time Comparison")
            plt.xlabel("Workload Count")
            plt.ylabel("Execution Time (seconds)")
            plt.grid(True, linestyle="--", alpha=0.7)
            plt.legend()
            plt.tight_layout()
            plt.savefig(f"{output_dir}/execution_time_comparison.png")

            logger.info(f"Plots saved to {output_dir}")

        except ImportError:
            logger.warning("Matplotlib not available - skipping plot generation")


async def main():
    """Run resource optimization algorithm benchmark"""
    logger.info("Starting resource optimization algorithm benchmark")

    benchmark = OptimizationBenchmark()

    # Test with increasing workload counts
    workload_counts = [10, 50, 100, 200]

    # Run benchmark
    results = benchmark.run_benchmark(workload_counts)

    # Analyze results
    analysis = benchmark.analyze_results(results)

    # Print summary
    print("\nResource Optimization Algorithm Results:")
    print("=======================================")

    for count in workload_counts:
        print(f"\nWorkload count: {count}")

        count_results = results[count]
        for algo_name, result in count_results.items():
            print(f"\n  Algorithm: {algo_name}")
            print(f"    Total hourly cost: ${result['total_hourly_cost']:.4f}")
            if "average_latency_ms" in result:
                print(f"    Average latency: {result['average_latency_ms']:.2f} ms")
            print(f"    Success rate: {result['allocation_success_rate'] * 100:.1f}%")
            print(f"    Execution time: {result['execution_time'] * 1000:.2f} ms")

    print("\nAnalysis:")

    # Compare algorithm performance for largest workload count
    largest_count = max(workload_counts)
    largest_analysis = analysis[largest_count]

    print(f"\nFor {largest_count} workloads:")

    # Cost-effectiveness (1.0 = baseline cost optimization)
    print("\n  Cost-effectiveness (lower is better):")
    for algo, value in largest_analysis["cost_comparison"].items():
        print(f"    {algo}: {value:.4f}x")

    # Latency-effectiveness (1.0 = baseline latency optimization)
    print("\n  Latency-effectiveness (lower is better):")
    for algo, value in largest_analysis["latency_comparison"].items():
        print(f"    {algo}: {value:.4f}x")

    # Generate plots
    benchmark.plot_results(results, analysis)

    # Save results to JSON
    with open("optimization_results.json", "w") as f:
        # Convert objects to serializable form
        simplified_results = {}
        for count, count_results in results.items():
            simplified_results[count] = {
                algo_name: {
                    k: v
                    for k, v in algo_result.items()
                    if k != "allocation"  # Skip allocation details for brevity
                }
                for algo_name, algo_result in count_results.items()
            }

        json.dump({"results": simplified_results, "analysis": analysis}, f, indent=2)

    print("\nResults saved to optimization_results.json")


if __name__ == "__main__":
    asyncio.run(main())
