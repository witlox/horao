#!/usr/bin/env python3
"""
Test Case: Distributed Testing Framework
Objective: Evaluate different approaches to distributed testing for cloud-native applications
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Test execution result"""

    test_id: str
    test_name: str
    status: str  # "passed", "failed", "skipped", "error"
    execution_time: float
    worker_id: str = None
    error_message: str = None
    system_info: Dict = field(default_factory=dict)


class DistributedTestRunner:
    """Base class for distributed test runners"""

    def __init__(self, project_root: str, test_dir: str = None):
        """
        Initialize distributed test runner

        Args:
            project_root: Path to project root
            test_dir: Path to test directory (relative to project_root)
        """
        self.project_root = Path(project_root)
        self.test_dir = self.project_root / (test_dir or "tests")
        self.results = []
        self.start_time = None
        self.end_time = None
        self.total_duration = None

    def discover_tests(self) -> List[str]:
        """
        Discover test files

        Returns:
            List of test file paths
        """
        test_files = []

        # Find all Python files that start with test_
        for test_file in self.test_dir.glob("**/*.py"):
            if test_file.name.startswith("test_"):
                test_files.append(str(test_file.relative_to(self.project_root)))

        logger.info(f"Discovered {len(test_files)} test files")
        return test_files

    def run(self, workers: int = 4) -> Dict:
        """
        Run tests in distributed manner

        Args:
            workers: Number of worker processes/threads

        Returns:
            Dictionary with test results
        """
        self.start_time = time.time()

        # Discover tests
        test_files = self.discover_tests()

        # Execute tests
        self._execute_tests(test_files, workers)

        self.end_time = time.time()
        self.total_duration = self.end_time - self.start_time

        # Generate report
        return self._generate_report()

    def _execute_tests(self, test_files: List[str], workers: int) -> None:
        """
        Execute tests in parallel

        Args:
            test_files: List of test files
            workers: Number of workers
        """
        raise NotImplementedError("Subclasses must implement _execute_tests")

    def _generate_report(self) -> Dict:
        """
        Generate test execution report

        Returns:
            Dictionary with test report
        """
        # Count results by status
        status_counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}

        for result in self.results:
            status = result.status.lower()
            if status in status_counts:
                status_counts[status] += 1
            else:
                status_counts["error"] += 1

        return {
            "summary": {
                "total_tests": len(self.results),
                "execution_time": self.total_duration,
                "success_rate": (
                    (status_counts["passed"] / len(self.results)) * 100
                    if self.results
                    else 0
                ),
                "status_counts": status_counts,
            },
            "results": [vars(r) for r in self.results],
        }


class ProcessPoolTestRunner(DistributedTestRunner):
    """Test runner using Python's ProcessPoolExecutor"""

    def _execute_tests(self, test_files: List[str], workers: int) -> None:
        """
        Execute tests using process pool

        Args:
            test_files: List of test files
            workers: Number of workers
        """
        logger.info(f"Running tests with ProcessPoolExecutor ({workers} workers)")

        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(self._run_test_file, test_file)
                for test_file in test_files
            ]

            for future in futures:
                results = future.result()
                if results:
                    self.results.extend(results)

    def _run_test_file(self, test_file: str) -> List[TestResult]:
        """
        Run a single test file

        Args:
            test_file: Path to test file

        Returns:
            List of TestResult objects
        """
        worker_id = f"process-{os.getpid()}"
        logger.info(f"Worker {worker_id} running {test_file}")

        test_path = self.project_root / test_file

        # Run pytest with JSON output
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(test_path),
            "--json-report",
            "--json-report-file=none",
        ]

        start_time = time.time()
        process = subprocess.run(
            cmd,
            cwd=str(self.project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, "PYTHONPATH": str(self.project_root)},
        )
        end_time = time.time()

        # Try to extract JSON report from stdout
        json_output = None
        try:
            output = process.stdout
            json_start = output.rfind("{")
            json_end = output.rfind("}")

            if json_start >= 0 and json_end >= 0:
                json_str = output[json_start : json_end + 1]
                json_output = json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Could not parse JSON output from {test_file}")

        results = []

        if json_output and "tests" in json_output:
            for test_data in json_output["tests"]:
                test_id = test_data.get("nodeid", str(uuid.uuid4()))
                test_name = test_id.split("::")[-1] if "::" in test_id else test_id

                status = test_data.get("outcome", "error")
                duration = test_data.get("duration", end_time - start_time)

                error_message = None
                if status in ["failed", "error"]:
                    error_message = test_data.get("call", {}).get(
                        "longrepr", "Unknown error"
                    )

                results.append(
                    TestResult(
                        test_id=test_id,
                        test_name=test_name,
                        status=status,
                        execution_time=duration,
                        worker_id=worker_id,
                        error_message=error_message,
                        system_info={"pid": os.getpid()},
                    )
                )
        else:
            # Fallback: Create a single result for the whole file
            results.append(
                TestResult(
                    test_id=test_file,
                    test_name=Path(test_file).stem,
                    status="error" if process.returncode != 0 else "passed",
                    execution_time=end_time - start_time,
                    worker_id=worker_id,
                    error_message=process.stderr if process.returncode != 0 else None,
                    system_info={"pid": os.getpid()},
                )
            )

        return results


class ThreadPoolTestRunner(DistributedTestRunner):
    """Test runner using Python's ThreadPoolExecutor"""

    def _execute_tests(self, test_files: List[str], workers: int) -> None:
        """
        Execute tests using thread pool

        Args:
            test_files: List of test files
            workers: Number of workers
        """
        logger.info(f"Running tests with ThreadPoolExecutor ({workers} workers)")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(self._run_test_file, test_file)
                for test_file in test_files
            ]

            for future in futures:
                results = future.result()
                if results:
                    self.results.extend(results)

    def _run_test_file(self, test_file: str) -> List[TestResult]:
        """
        Run a single test file

        Args:
            test_file: Path to test file

        Returns:
            List of TestResult objects
        """
        worker_id = f"thread-{threading.get_ident()}"
        logger.info(f"Worker {worker_id} running {test_file}")

        # Implementation similar to ProcessPoolTestRunner._run_test_file
        test_path = self.project_root / test_file

        # Run pytest with JSON output
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(test_path),
            "--json-report",
            "--json-report-file=none",
        ]

        start_time = time.time()
        process = subprocess.run(
            cmd,
            cwd=str(self.project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, "PYTHONPATH": str(self.project_root)},
        )
        end_time = time.time()

        # Process results (same as in ProcessPoolTestRunner)
        # Try to extract JSON report from stdout
        json_output = None
        try:
            output = process.stdout
            json_start = output.rfind("{")
            json_end = output.rfind("}")

            if json_start >= 0 and json_end >= 0:
                json_str = output[json_start : json_end + 1]
                json_output = json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Could not parse JSON output from {test_file}")

        results = []

        if json_output and "tests" in json_output:
            for test_data in json_output["tests"]:
                test_id = test_data.get("nodeid", str(uuid.uuid4()))
                test_name = test_id.split("::")[-1] if "::" in test_id else test_id

                status = test_data.get("outcome", "error")
                duration = test_data.get("duration", end_time - start_time)

                error_message = None
                if status in ["failed", "error"]:
                    error_message = test_data.get("call", {}).get(
                        "longrepr", "Unknown error"
                    )

                results.append(
                    TestResult(
                        test_id=test_id,
                        test_name=test_name,
                        status=status,
                        execution_time=duration,
                        worker_id=worker_id,
                        error_message=error_message,
                        system_info={"thread_id": threading.get_ident()},
                    )
                )
        else:
            # Fallback: Create a single result for the whole file
            results.append(
                TestResult(
                    test_id=test_file,
                    test_name=Path(test_file).stem,
                    status="error" if process.returncode != 0 else "passed",
                    execution_time=end_time - start_time,
                    worker_id=worker_id,
                    error_message=process.stderr if process.returncode != 0 else None,
                    system_info={"thread_id": threading.get_ident()},
                )
            )

        return results


class AsyncRunner(DistributedTestRunner):
    """Test runner using asyncio for concurrent test execution"""

    async def _run_test_file_async(self, test_file: str) -> List[TestResult]:
        """
        Run a single test file asynchronously

        Args:
            test_file: Path to test file

        Returns:
            List of TestResult objects
        """
        worker_id = f"async-{id(asyncio.current_task())}"
        logger.info(f"Worker {worker_id} running {test_file}")

        test_path = self.project_root / test_file

        # Run pytest with JSON output
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(test_path),
            "--json-report",
            "--json-report-file=none",
        ]

        start_time = time.time()
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.project_root),
            env={**os.environ, "PYTHONPATH": str(self.project_root)},
        )

        stdout, stderr = await proc.communicate()
        end_time = time.time()

        # Try to extract JSON report from stdout
        json_output = None
        try:
            output = stdout.decode()
            json_start = output.rfind("{")
            json_end = output.rfind("}")

            if json_start >= 0 and json_end >= 0:
                json_str = output[json_start : json_end + 1]
                json_output = json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Could not parse JSON output from {test_file}")

        results = []

        if json_output and "tests" in json_output:
            for test_data in json_output["tests"]:
                test_id = test_data.get("nodeid", str(uuid.uuid4()))
                test_name = test_id.split("::")[-1] if "::" in test_id else test_id

                status = test_data.get("outcome", "error")
                duration = test_data.get("duration", end_time - start_time)

                error_message = None
                if status in ["failed", "error"]:
                    error_message = test_data.get("call", {}).get(
                        "longrepr", "Unknown error"
                    )

                results.append(
                    TestResult(
                        test_id=test_id,
                        test_name=test_name,
                        status=status,
                        execution_time=duration,
                        worker_id=worker_id,
                        error_message=error_message,
                        system_info={"task_id": id(asyncio.current_task())},
                    )
                )
        else:
            # Fallback: Create a single result for the whole file
            results.append(
                TestResult(
                    test_id=test_file,
                    test_name=Path(test_file).stem,
                    status="error" if proc.returncode != 0 else "passed",
                    execution_time=end_time - start_time,
                    worker_id=worker_id,
                    error_message=stderr.decode() if proc.returncode != 0 else None,
                    system_info={"task_id": id(asyncio.current_task())},
                )
            )

        return results

    def _execute_tests(self, test_files: List[str], workers: int) -> None:
        """
        Execute tests using asyncio

        Args:
            test_files: List of test files
            workers: Number of workers
        """
        logger.info(f"Running tests with asyncio ({workers} concurrent tasks)")

        # Create event loop and run async code
        loop = asyncio.get_event_loop()
        self.results = loop.run_until_complete(
            self._execute_tests_async(test_files, workers)
        )

    async def _execute_tests_async(
        self, test_files: List[str], workers: int
    ) -> List[TestResult]:
        """
        Execute tests asynchronously

        Args:
            test_files: List of test files
            workers: Number of workers

        Returns:
            List of TestResult objects
        """
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(workers)

        async def run_with_semaphore(test_file):
            async with semaphore:
                return await self._run_test_file_async(test_file)

        # Run tests concurrently with limited concurrency
        tasks = [run_with_semaphore(test_file) for test_file in test_files]
        results = await asyncio.gather(*tasks)

        # Flatten results
        flattened = []
        for result in results:
            if result:
                flattened.extend(result)

        return flattened


class DistributedTestOrchestrator:
    """Coordinates distributed test execution across multiple strategies"""

    def __init__(self, project_root: str, test_dir: str = None):
        """
        Initialize test orchestrator

        Args:
            project_root: Path to project root
            test_dir: Path to test directory (relative to project_root)
        """
        self.project_root = Path(project_root)
        self.test_dir = test_dir or "tests"
        self.results = {}

    def run_comparison(
        self, worker_counts: List[int] = None, iterations: int = 3
    ) -> Dict:
        """
        Run tests using different strategies and compare results

        Args:
            worker_counts: List of worker counts to test
            iterations: Number of iterations for each configuration

        Returns:
            Dictionary with comparison results
        """
        if worker_counts is None:
            worker_counts = [1, 2, 4]

        logger.info(f"Running distributed test comparison with {iterations} iterations")

        strategies = {
            "process_pool": ProcessPoolTestRunner,
            "thread_pool": ThreadPoolTestRunner,
            "async": AsyncRunner,
        }

        results = {
            "project_root": str(self.project_root),
            "test_dir": self.test_dir,
            "worker_counts": worker_counts,
            "iterations": iterations,
            "strategies": {},
            "comparative_analysis": {},
        }

        # Run each strategy with each worker count
        for strategy_name, strategy_class in strategies.items():
            results["strategies"][strategy_name] = {}

            for workers in worker_counts:
                # Run multiple iterations
                iteration_results = []

                for i in range(iterations):
                    logger.info(
                        f"Running {strategy_name} with {workers} workers (iteration {i+1}/{iterations})"
                    )

                    runner = strategy_class(self.project_root, self.test_dir)
                    result = runner.run(workers)

                    iteration_results.append(
                        {
                            "execution_time": result["summary"]["execution_time"],
                            "success_rate": result["summary"]["success_rate"],
                            "test_count": result["summary"]["total_tests"],
                        }
                    )

                # Calculate averages
                avg_time = sum(r["execution_time"] for r in iteration_results) / len(
                    iteration_results
                )
                avg_success = sum(r["success_rate"] for r in iteration_results) / len(
                    iteration_results
                )
                test_count = iteration_results[0][
                    "test_count"
                ]  # Should be the same for all iterations

                results["strategies"][strategy_name][workers] = {
                    "average_execution_time": avg_time,
                    "average_success_rate": avg_success,
                    "test_count": test_count,
                    "iterations": iteration_results,
                }

        # Comparative analysis
        for workers in worker_counts:
            # Find fastest strategy for each worker count
            strategy_times = {
                strategy: results["strategies"][strategy][workers][
                    "average_execution_time"
                ]
                for strategy in strategies
            }

            fastest = min(strategy_times, key=strategy_times.get)
            slowest = max(strategy_times, key=strategy_times.get)

            # Speed comparison
            speedup = {}
            for strategy in strategies:
                reference_time = strategy_times[fastest]
                if reference_time > 0:
                    relative_time = strategy_times[strategy] / reference_time
                    speedup[strategy] = relative_time
                else:
                    speedup[strategy] = 1.0

            results["comparative_analysis"][workers] = {
                "fastest_strategy": fastest,
                "slowest_strategy": slowest,
                "relative_speeds": speedup,
                "execution_times": {s: strategy_times[s] for s in strategies},
            }

        # Overall recommendations
        recommendations = []

        # Find best overall strategy
        overall_best = None
        best_avg_time = float("inf")

        for strategy in strategies:
            # Average execution time across all worker counts
            avg_times = [
                results["strategies"][strategy][workers]["average_execution_time"]
                for workers in worker_counts
            ]
            avg_time = sum(avg_times) / len(avg_times)

            if avg_time < best_avg_time:
                best_avg_time = avg_time
                overall_best = strategy

        recommendations.append(f"Overall best strategy: {overall_best}")

        # Find optimal worker count for the best strategy
        best_worker_count = min(
            worker_counts,
            key=lambda w: results["strategies"][overall_best][w][
                "average_execution_time"
            ],
        )

        recommendations.append(
            f"Optimal worker count for {overall_best}: {best_worker_count}"
        )

        # Check if there's significant difference between strategies
        baseline = results["strategies"][overall_best][best_worker_count][
            "average_execution_time"
        ]

        for strategy in strategies:
            if strategy == overall_best:
                continue

            strategy_time = results["strategies"][strategy][best_worker_count][
                "average_execution_time"
            ]
            diff_pct = ((strategy_time - baseline) / baseline) * 100

            if abs(diff_pct) < 5:
                recommendations.append(
                    f"{strategy} is within 5% of {overall_best} performance with {best_worker_count} workers"
                )

        results["recommendations"] = recommendations
        self.results = results

        return results

    def generate_report(self, output_file: str = None) -> Dict:
        """
        Generate comprehensive report of test execution

        Args:
            output_file: Path to write report JSON

        Returns:
            Report dictionary
        """
        if not self.results:
            return {"error": "No test results available. Run run_comparison() first."}

        # Add time/date information
        self.results["report_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

        # Write to file if requested
        if output_file:
            output_path = Path(output_file)
            os.makedirs(output_path.parent, exist_ok=True)

            with open(output_path, "w") as f:
                json.dump(self.results, f, indent=2)

            logger.info(f"Report written to {output_path}")

        return self.results


# Import threading here to avoid issues with ProcessPoolExecutor on module level
import threading


def main():
    """Run distributed testing comparison"""
    logger.info("Starting Distributed Testing Evaluation")

    # Find project root
    project_root = Path(__file__).parent.parent.parent

    print("\nDistributed Testing Evaluation")
    print("=============================\n")

    print(f"Project root: {project_root}")

    # Configure test parameters
    worker_counts = [1, 2, 4, 8]
    iterations = 3

    # Prompt for configuration changes
    print("\nTest Configuration:")
    print(f"  Worker counts to test: {worker_counts}")
    print(f"  Iterations per configuration: {iterations}")

    change_config = input("\nChange configuration? (y/n): ").strip().lower() == "y"
    if change_config:
        worker_input = input("Worker counts (comma-separated, e.g. 1,2,4,8): ").strip()
        if worker_input:
            try:
                worker_counts = [int(w.strip()) for w in worker_input.split(",")]
            except ValueError:
                print("Invalid worker counts. Using defaults.")

        iterations_input = input("Iterations (1-10): ").strip()
        if iterations_input:
            try:
                iterations = max(1, min(10, int(iterations_input)))
            except ValueError:
                print("Invalid iteration count. Using default.")

    # Run comparison
    print(
        f"\nRunning comparison with {len(worker_counts)} worker counts and {iterations} iterations..."
    )
    print("This may take several minutes depending on the size of your test suite.")

    orchestrator = DistributedTestOrchestrator(project_root)
    results = orchestrator.run_comparison(worker_counts, iterations)

    # Generate report
    report_path = (
        project_root
        / "research"
        / "devops_practices"
        / "distributed_testing_report.json"
    )
    orchestrator.generate_report(str(report_path))

    # Print summary
    print("\nTest Execution Summary:")
    for workers in worker_counts:
        print(f"\n  Workers: {workers}")
        for strategy, data in results["comparative_analysis"][workers][
            "execution_times"
        ].items():
            print(f"    {strategy}: {data:.2f}s")

    # Print recommendations
    print("\nRecommendations:")
    for i, rec in enumerate(results["recommendations"], 1):
        print(f"  {i}. {rec}")

    print(f"\nDetailed report saved to: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
