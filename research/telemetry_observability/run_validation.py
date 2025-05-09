#!/usr/bin/env python3
"""
Validation Framework: Telemetry and Observability Validation
Objective: Validate telemetry collection and observability mechanisms
"""

import argparse
import asyncio
import importlib
import inspect
import json
import logging
import sys
import time
from pathlib import Path

# Add project root to path so we can import HORAO modules
sys.path.append(str(Path(__file__).parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ValidationSuite:
    """Loads and runs all telemetry and observability test cases for validation"""

    def __init__(self):
        """Initialize the validation suite"""
        self.test_modules = {}
        self.test_results = {}

    async def load_test_modules(self):
        """Load all test modules in the current directory"""
        test_files = ["test_distributed_tracing", "test_sampling_strategies"]

        for module_name in test_files:
            try:
                # Import the module dynamically
                module = importlib.import_module(module_name)
                self.test_modules[module_name] = module
                logger.info(f"Loaded test module: {module_name}")
            except ImportError as e:
                logger.warning(f"Failed to import {module_name}: {e}")

        return len(self.test_modules)

    def _is_test_coroutine(self, obj):
        """Check if an object is an async test function"""
        return inspect.iscoroutinefunction(obj) and (
            obj.__name__.startswith("test_") or obj.__name__ == "main"
        )

    async def _run_test_coroutine(self, coro_func, module_name):
        """Run a test coroutine and capture its result"""
        try:
            start_time = time.time()
            if inspect.iscoroutinefunction(coro_func):
                # If the function is an async coroutine, await it
                result = await coro_func()
            else:
                # Otherwise just call it
                result = coro_func()

            elapsed_time = time.time() - start_time

            return {
                "status": "success",
                "elapsed_seconds": elapsed_time,
                "result": result,
            }
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(
                f"Error in {module_name}.{coro_func.__name__}: {e}", exc_info=True
            )
            return {
                "status": "error",
                "elapsed_seconds": elapsed_time,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    async def run_validation(self, specific_test=None):
        """Run validation tests from all modules"""
        validation_results = {}

        # Find which modules to run
        modules_to_run = {}
        if specific_test:
            # Run only the specified test
            for module_name, module in self.test_modules.items():
                if specific_test in module_name:
                    modules_to_run[module_name] = module
        else:
            # Run all modules
            modules_to_run = self.test_modules

        # For each module, find and run test functions
        for module_name, module in modules_to_run.items():
            module_results = {}

            # Find all test coroutines in the module
            test_coroutines = inspect.getmembers(
                module, predicate=self._is_test_coroutine
            )

            # Run each test coroutine
            for name, coro_func in test_coroutines:
                logger.info(f"Running {module_name}.{name}")
                result = await self._run_test_coroutine(coro_func, module_name)
                module_results[name] = result

            validation_results[module_name] = module_results

        self.test_results = validation_results
        return validation_results

    def analyze_results(self):
        """Analyze validation results across all tests"""
        if not self.test_results:
            return {"error": "No test results available"}

        analysis = {
            "total_tests": 0,
            "successful_tests": 0,
            "failed_tests": 0,
            "modules_run": len(self.test_results),
            "total_duration_seconds": 0,
            "tests_by_module": {},
            "telemetry_metrics": {},
        }

        # Process each module's results
        for module_name, module_results in self.test_results.items():
            module_analysis = {
                "total_tests": len(module_results),
                "successful_tests": sum(
                    1 for r in module_results.values() if r.get("status") == "success"
                ),
                "failed_tests": sum(
                    1 for r in module_results.values() if r.get("status") == "error"
                ),
                "total_duration_seconds": sum(
                    r.get("elapsed_seconds", 0) for r in module_results.values()
                ),
            }

            analysis["tests_by_module"][module_name] = module_analysis
            analysis["total_tests"] += module_analysis["total_tests"]
            analysis["successful_tests"] += module_analysis["successful_tests"]
            analysis["failed_tests"] += module_analysis["failed_tests"]
            analysis["total_duration_seconds"] += module_analysis[
                "total_duration_seconds"
            ]

            # Extract telemetry metrics from test results
            for test_name, test_result in module_results.items():
                if test_result.get("status") == "success" and isinstance(
                    test_result.get("result"), dict
                ):

                    result_data = test_result.get("result", {})

                    # Look for common telemetry metrics in the results
                    for metric_key in [
                        "trace_coverage_percent",
                        "sampling_efficiency",
                        "trace_latency_ms",
                        "correlation_accuracy",
                        "overhead_percent",
                        "telemetry_data_size_kb",
                    ]:
                        if metric_key in result_data:
                            if metric_key not in analysis["telemetry_metrics"]:
                                analysis["telemetry_metrics"][metric_key] = []

                            analysis["telemetry_metrics"][metric_key].append(
                                {
                                    "module": module_name,
                                    "test": test_name,
                                    "value": result_data[metric_key],
                                }
                            )

        # Calculate aggregate telemetry metrics
        for metric_key in [
            "trace_coverage_percent",
            "sampling_efficiency",
            "overhead_percent",
        ]:
            if metric_key in analysis["telemetry_metrics"]:
                values = [
                    item["value"]
                    for item in analysis["telemetry_metrics"][metric_key]
                    if isinstance(item["value"], (int, float))
                ]
                if values:
                    analysis[f"avg_{metric_key}"] = sum(values) / len(values)

        # Calculate average trace latency if available
        if "trace_latency_ms" in analysis["telemetry_metrics"]:
            values = [
                item["value"]
                for item in analysis["telemetry_metrics"]["trace_latency_ms"]
                if isinstance(item["value"], (int, float))
            ]
            if values:
                analysis["avg_trace_latency_ms"] = sum(values) / len(values)
                analysis["p95_trace_latency_ms"] = sorted(values)[
                    int(len(values) * 0.95)
                ]

        # Calculate telemetry effectiveness score
        if (
            "avg_trace_coverage_percent" in analysis
            and "avg_overhead_percent" in analysis
        ):
            # Higher coverage and lower overhead is better
            coverage = analysis["avg_trace_coverage_percent"]
            overhead = analysis["avg_overhead_percent"]

            # Simple formula: coverage - overhead/2 (penalize overhead but not as much as coverage matters)
            effectiveness = coverage - (overhead / 2)
            analysis["telemetry_effectiveness_score"] = max(0, min(100, effectiveness))

        return analysis


async def run_telemetry_validation(
    specific_test=None, output_file="telemetry_validation_results.json"
):
    """Run the full telemetry and observability validation suite"""
    logger.info("Starting telemetry and observability validation framework")

    # Create and load validation suite
    suite = ValidationSuite()
    loaded_count = await suite.load_test_modules()
    logger.info(f"Loaded {loaded_count} test modules")

    if loaded_count == 0:
        logger.error("No test modules were loaded. Validation cannot proceed.")
        return False

    # Run validation
    logger.info(f"Running {'specified tests' if specific_test else 'all tests'}")
    results = await suite.run_validation(specific_test)

    # Analyze results
    analysis = suite.analyze_results()

    # Combine results and analysis
    output_data = {"results": results, "analysis": analysis}

    # Save to file
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"Validation complete. Results saved to {output_file}")

    # Print summary to console
    print("\nTelemetry and Observability Validation Summary:")
    print("=============================================")
    print(f"Total tests run: {analysis['total_tests']}")
    print(f"Successful: {analysis['successful_tests']}")
    print(f"Failed: {analysis['failed_tests']}")
    print(f"Total duration: {analysis['total_duration_seconds']:.2f} seconds")

    if "avg_trace_coverage_percent" in analysis:
        print(
            f"\nAverage trace coverage: {analysis['avg_trace_coverage_percent']:.2f}%"
        )

    if "avg_overhead_percent" in analysis:
        print(f"Average telemetry overhead: {analysis['avg_overhead_percent']:.2f}%")

    if "avg_trace_latency_ms" in analysis:
        print(f"Average trace latency: {analysis['avg_trace_latency_ms']:.2f}ms")

    if "telemetry_effectiveness_score" in analysis:
        print(
            f"Telemetry effectiveness score: {analysis['telemetry_effectiveness_score']:.2f}/100"
        )

    # Return success if all tests passed
    return analysis["failed_tests"] == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run telemetry and observability validation framework"
    )
    parser.add_argument("--test", help="Specific test to run (partial module name)")
    parser.add_argument(
        "--output",
        default="telemetry_validation_results.json",
        help="Output file for validation results",
    )

    args = parser.parse_args()

    asyncio.run(run_telemetry_validation(args.test, args.output))
