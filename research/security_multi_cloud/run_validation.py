#!/usr/bin/env python3
"""
Validation Framework: Security Multi-Cloud Validation
Objective: Validate security mechanisms for multi-cloud environments
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
    """Loads and runs all security test cases for validation"""

    def __init__(self):
        """Initialize the validation suite"""
        self.test_modules = {}
        self.test_results = {}

    async def load_test_modules(self):
        """Load all test modules in the current directory"""
        test_files = [
            "test_peer_authentication",
            "test_communication_security",
            "test_authorization_boundaries",
        ]

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
            "security_metrics": {},
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

            # Extract security metrics from test results
            for test_name, test_result in module_results.items():
                if test_result.get("status") == "success" and isinstance(
                    test_result.get("result"), dict
                ):

                    result_data = test_result.get("result", {})

                    # Look for common security metrics in the results
                    for metric_key in [
                        "auth_failures",
                        "security_score",
                        "forgery_detection_rate",
                        "mitm_prevention_score",
                        "auth_latency_ms",
                        "boundary_violations",
                    ]:
                        if metric_key in result_data:
                            if metric_key not in analysis["security_metrics"]:
                                analysis["security_metrics"][metric_key] = []

                            analysis["security_metrics"][metric_key].append(
                                {
                                    "module": module_name,
                                    "test": test_name,
                                    "value": result_data[metric_key],
                                }
                            )

                    # Look in summary field for nested metrics
                    if "summary" in result_data and isinstance(
                        result_data["summary"], dict
                    ):
                        summary = result_data["summary"]
                        for metric_key in ["security_score", "percentage_score"]:
                            if metric_key in summary:
                                if metric_key not in analysis["security_metrics"]:
                                    analysis["security_metrics"][metric_key] = []

                                analysis["security_metrics"][metric_key].append(
                                    {
                                        "module": module_name,
                                        "test": test_name,
                                        "value": summary[metric_key],
                                    }
                                )

        # Calculate aggregate security metrics
        for metric_key in [
            "security_score",
            "percentage_score",
            "forgery_detection_rate",
        ]:
            if metric_key in analysis["security_metrics"]:
                values = [
                    item["value"]
                    for item in analysis["security_metrics"][metric_key]
                    if isinstance(item["value"], (int, float))
                ]
                if values:
                    analysis[f"avg_{metric_key}"] = sum(values) / len(values)

        # Compute overall security rating
        if "avg_percentage_score" in analysis:
            score = analysis["avg_percentage_score"]
            analysis["security_rating"] = (
                "Excellent"
                if score >= 90
                else (
                    "Good"
                    if score >= 75
                    else (
                        "Satisfactory"
                        if score >= 60
                        else "Needs Improvement" if score >= 40 else "Inadequate"
                    )
                )
            )

        return analysis


async def run_security_validation(
    specific_test=None, output_file="security_validation_results.json"
):
    """Run the full security multi-cloud validation suite"""
    logger.info("Starting security multi-cloud validation framework")

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
    print("\nSecurity Multi-Cloud Validation Summary:")
    print("=====================================")
    print(f"Total tests run: {analysis['total_tests']}")
    print(f"Successful: {analysis['successful_tests']}")
    print(f"Failed: {analysis['failed_tests']}")
    print(f"Total duration: {analysis['total_duration_seconds']:.2f} seconds")

    if "security_rating" in analysis:
        print(f"\nOverall Security Rating: {analysis['security_rating']}")

    if "avg_percentage_score" in analysis:
        print(f"Average Security Score: {analysis['avg_percentage_score']:.2f}%")

    # Return success if all tests passed
    return analysis["failed_tests"] == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run security multi-cloud validation framework"
    )
    parser.add_argument("--test", help="Specific test to run (partial module name)")
    parser.add_argument(
        "--output",
        default="security_validation_results.json",
        help="Output file for validation results",
    )

    args = parser.parse_args()

    asyncio.run(run_security_validation(args.test, args.output))
