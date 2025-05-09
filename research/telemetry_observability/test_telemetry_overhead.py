#!/usr/bin/env python3
"""
Test Case: Telemetry Overhead Measurement
Objective: Quantify the performance impact of different telemetry configurations
"""

import asyncio
import logging
import os
import statistics
import sys
import time
import tracemalloc
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add project root to path so we can import HORAO modules
sys.path.append(str(Path(__file__).parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TelemetryConfig:
    """Represents a telemetry configuration for testing"""

    def __init__(
        self, name: str, trace_level: str = "info", metrics_interval: float = 15.0
    ):
        self.name = name
        self.trace_level = trace_level  # "off", "error", "warn", "info", "debug", "all"
        self.metrics_interval = metrics_interval  # seconds

    def apply(self):
        """Apply this configuration to the environment"""
        logger.info(f"Applying telemetry configuration: {self.name}")

        # Set environment variables to configure telemetry
        os.environ["OTEL_TRACES_SAMPLER"] = (
            "always_on" if self.trace_level != "off" else "always_off"
        )
        os.environ["OTEL_LOG_LEVEL"] = (
            self.trace_level if self.trace_level != "off" else "error"
        )
        os.environ["OTEL_METRICS_EXPORT_INTERVAL"] = str(
            int(self.metrics_interval * 1000)
        )  # Convert to milliseconds

        # In a real test, we would reload the telemetry configuration here
        # For simulation, we just pretend it happened
        logger.info(
            f"Telemetry configuration applied: traces={self.trace_level}, metrics_interval={self.metrics_interval}s"
        )


@contextmanager
def measure_resource_usage():
    """Context manager to measure CPU and memory usage"""
    tracemalloc.start()
    start_time = time.time()

    yield

    elapsed_time = time.time() - start_time
    current_memory, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Return time in ms, memory in MB
    result = {
        "elapsed_time_ms": elapsed_time * 1000,
        "memory_current_mb": current_memory / (1024 * 1024),
        "memory_peak_mb": peak_memory / (1024 * 1024),
    }

    return result


class TelemetryWorkload:
    """Simulates a workload to measure telemetry overhead"""

    def __init__(self, name: str, operation_count: int = 1000):
        self.name = name
        self.operation_count = operation_count

    async def run(self) -> Dict:
        """Run the workload and measure resource usage"""
        logger.info(
            f"Running workload: {self.name} with {self.operation_count} operations"
        )

        with measure_resource_usage() as usage:
            # Simulating a workload with a mix of operations
            for i in range(self.operation_count):
                if i % 10 == 0:
                    await self._simulate_resource_operation("create", i)
                elif i % 10 == 1:
                    await self._simulate_resource_operation("update", i)
                elif i % 10 == 2:
                    await self._simulate_resource_operation("delete", i)
                else:
                    await self._simulate_resource_operation("read", i)

        logger.info(f"Workload {self.name} completed. Usage: {usage}")
        return usage

    async def _simulate_resource_operation(self, op_type: str, index: int):
        """Simulate a resource operation with telemetry instrumentation"""
        # In a real system, we'd capture spans, metrics, and logs here
        # For simulation, we just add a small delay based on telemetry config

        # Determine how much "instrumentation" to simulate based on env vars
        trace_level = os.environ.get("OTEL_LOG_LEVEL", "info")
        trace_enabled = (
            os.environ.get("OTEL_TRACES_SAMPLER", "always_on") == "always_on"
        )

        # More telemetry means more overhead (simulated)
        if trace_enabled:
            if trace_level == "debug":
                # Heavy instrumentation
                await asyncio.sleep(0.001)
            elif trace_level == "info":
                # Medium instrumentation
                await asyncio.sleep(0.0005)
            else:
                # Light instrumentation
                await asyncio.sleep(0.0001)

        # Simulate the actual operation (equal for all configs)
        await asyncio.sleep(0.001)


class TelemetryBenchmark:
    """Benchmark harness for telemetry overhead testing"""

    def __init__(self):
        # Define telemetry configurations to test
        self.configurations = [
            TelemetryConfig("minimal", trace_level="error", metrics_interval=60.0),
            TelemetryConfig("standard", trace_level="info", metrics_interval=15.0),
            TelemetryConfig("verbose", trace_level="debug", metrics_interval=5.0),
            TelemetryConfig("trace_off", trace_level="off", metrics_interval=15.0),
        ]

        # Define workloads to test with
        self.workloads = [
            TelemetryWorkload("small", operation_count=100),
            TelemetryWorkload("medium", operation_count=500),
            TelemetryWorkload("large", operation_count=1000),
        ]

    async def run_benchmarks(self, iterations: int = 3) -> Dict:
        """
        Run benchmarks for all configurations and workloads

        Args:
            iterations: Number of iterations to run for each config/workload

        Returns:
            Dictionary with benchmark results
        """
        results = {}

        for config in self.configurations:
            config_results = {}

            # Apply this telemetry configuration
            config.apply()

            for workload in self.workloads:
                workload_results = []

                # Run multiple iterations
                for i in range(iterations):
                    logger.info(
                        f"Running iteration {i+1}/{iterations} for {config.name}/{workload.name}"
                    )
                    result = await workload.run()
                    workload_results.append(result)

                # Calculate statistics across iterations
                elapsed_times = [r["elapsed_time_ms"] for r in workload_results]
                memory_peaks = [r["memory_peak_mb"] for r in workload_results]

                stats = {
                    "elapsed_time_ms": {
                        "mean": statistics.mean(elapsed_times),
                        "median": statistics.median(elapsed_times),
                        "min": min(elapsed_times),
                        "max": max(elapsed_times),
                    },
                    "memory_peak_mb": {
                        "mean": statistics.mean(memory_peaks),
                        "median": statistics.median(memory_peaks),
                        "min": min(memory_peaks),
                        "max": max(memory_peaks),
                    },
                    "iterations": iterations,
                    "raw_results": workload_results,
                }

                config_results[workload.name] = stats

            results[config.name] = config_results

        return results

    def analyze_results(self, results: Dict) -> Dict:
        """
        Analyze benchmark results to quantify overhead

        Args:
            results: Dictionary with benchmark results

        Returns:
            Dictionary with analysis
        """
        analysis = {}

        # Use trace_off configuration as baseline
        if "trace_off" in results:
            baseline_config = "trace_off"

            for workload_name in results[baseline_config]:
                workload_analysis = {}

                baseline = results[baseline_config][workload_name]
                baseline_time = baseline["elapsed_time_ms"]["mean"]
                baseline_memory = baseline["memory_peak_mb"]["mean"]

                for config_name, config_results in results.items():
                    if (
                        config_name != baseline_config
                        and workload_name in config_results
                    ):
                        config_time = config_results[workload_name]["elapsed_time_ms"][
                            "mean"
                        ]
                        config_memory = config_results[workload_name]["memory_peak_mb"][
                            "mean"
                        ]

                        time_overhead = (
                            (config_time - baseline_time) / baseline_time
                        ) * 100
                        memory_overhead = (
                            (config_memory - baseline_memory) / baseline_memory
                        ) * 100

                        workload_analysis[config_name] = {
                            "time_overhead_percent": time_overhead,
                            "memory_overhead_percent": memory_overhead,
                            "absolute_time_ms": config_time,
                            "absolute_memory_mb": config_memory,
                        }

                analysis[workload_name] = workload_analysis

        return analysis


async def main():
    """Run the telemetry overhead benchmark suite"""
    logger.info("Starting telemetry overhead benchmark")

    benchmark = TelemetryBenchmark()

    # Run benchmarks
    results = await benchmark.run_benchmarks(iterations=3)

    # Analyze results
    analysis = benchmark.analyze_results(results)

    # Print summary
    print("\nTelemetry Overhead Benchmark Results:")
    print("====================================")

    for workload_name, workload_analysis in analysis.items():
        print(f"\nWorkload: {workload_name}")

        for config_name, metrics in workload_analysis.items():
            print(f"  Configuration: {config_name}")
            print(f"    Time Overhead: {metrics['time_overhead_percent']:.2f}%")
            print(f"    Memory Overhead: {metrics['memory_overhead_percent']:.2f}%")
            print(f"    Absolute Time: {metrics['absolute_time_ms']:.2f}ms")
            print(f"    Absolute Memory: {metrics['absolute_memory_mb']:.2f}MB")

    # Recommendations based on analysis
    print("\nRecommendations:")

    # Find configuration with best balance of overhead vs verbosity
    best_configs = {}
    for workload_name, workload_analysis in analysis.items():
        # Simple heuristic: minimize (time_overhead * 0.7 + memory_overhead * 0.3)
        best_config = min(
            workload_analysis.items(),
            key=lambda x: x[1]["time_overhead_percent"] * 0.7
            + x[1]["memory_overhead_percent"] * 0.3,
        )
        best_configs[workload_name] = best_config[0]

    for workload, config in best_configs.items():
        print(
            f"  For {workload} workloads: {config} configuration provides the best balance"
        )


if __name__ == "__main__":
    asyncio.run(main())
