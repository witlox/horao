#!/usr/bin/env python3
"""
Test Case: Distributed Tracing Analysis
Objective: Evaluate the effectiveness of distributed tracing in multi-cloud environments
"""

import asyncio
import json
import logging
import random
import sys
import time
import uuid
from pathlib import Path

# Add project root to path so we can import HORAO modules
sys.path.append(str(Path(__file__).parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor


class TraceContext:
    """Mock or real trace context depending on OpenTelemetry availability"""

    def __init__(self, name, attributes=None):
        self.name = name
        self.attributes = attributes or {}
        self.span_id = str(uuid.uuid4())[:8]
        self.trace_id = str(uuid.uuid4())
        self.parent_id = None
        self.start_time = time.time_ns()
        self.end_time = None
        self.events = []
        self.tracer = trace.get_tracer(__name__)
        self.span = self.tracer.start_span(name, attributes=attributes)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end()

    def add_event(self, name, attributes=None):
        """Add an event to the span"""
        event_time = time.time_ns()
        event = {"name": name, "timestamp": event_time, "attributes": attributes or {}}
        self.events.append(event)
        self.span.add_event(name, attributes)

    def set_attribute(self, key, value):
        """Set a span attribute"""
        self.attributes[key] = value
        self.span.set_attribute(key, value)

    def record_exception(self, exception, attributes=None):
        """Record an exception in the span"""
        self.add_event(
            "exception",
            {
                "exception.type": exception.__class__.__name__,
                "exception.message": str(exception),
                **(attributes or {}),
            },
        )

        if self.span:
            self.span.record_exception(exception, attributes)

    def end(self):
        """End the span"""
        self.end_time = time.time_ns()

        if self.span:
            self.span.end()

    def to_dict(self):
        """Convert span to dictionary representation"""
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": (
                (self.end_time - self.start_time) / 1_000_000 if self.end_time else None
            ),
            "attributes": self.attributes,
            "events": self.events,
        }


class CloudEnvironment:
    """Represents a cloud environment that can generate traces"""

    def __init__(self, name, region):
        self.name = name
        self.region = region
        self.trace_contexts = {}  # Map of trace_id -> list of spans

    def start_trace(self, operation_name, attributes=None):
        """Start a new trace"""
        context = TraceContext(
            operation_name,
            attributes={
                "cloud": self.name,
                "region": self.region,
                **(attributes or {}),
            },
        )

        # Store the trace context
        if context.trace_id not in self.trace_contexts:
            self.trace_contexts[context.trace_id] = []
        self.trace_contexts[context.trace_id].append(context)

        return context

    def continue_trace(self, parent_context, operation_name, attributes=None):
        """Continue a trace with a child span"""
        child_context = TraceContext(
            operation_name,
            attributes={
                "cloud": self.name,
                "region": self.region,
                **(attributes or {}),
            },
        )

        # Link to parent
        child_context.trace_id = parent_context.trace_id
        child_context.parent_id = parent_context.span_id

        # Store the trace context
        if child_context.trace_id not in self.trace_contexts:
            self.trace_contexts[child_context.trace_id] = []
        self.trace_contexts[child_context.trace_id].append(child_context)

        return child_context

    async def simulate_operation(
        self, parent_context=None, operation=None, duration_ms=None
    ):
        """Simulate a traced operation in this environment"""
        if operation is None:
            operations = [
                "provision_vm",
                "provision_storage",
                "provision_network",
                "query_resources",
                "update_resource",
                "delete_resource",
            ]
            operation = random.choice(operations)

        if duration_ms is None:
            # Different operations have different typical durations
            if "provision" in operation:
                duration_ms = random.uniform(500, 2000)  # Longer for provisioning
            elif "delete" in operation:
                duration_ms = random.uniform(300, 1000)
            elif "update" in operation:
                duration_ms = random.uniform(100, 500)
            else:
                duration_ms = random.uniform(50, 200)

        # Start the span (either a new trace or continuing an existing one)
        if parent_context is None:
            context = self.start_trace(
                operation, {"operation_type": operation.split("_")[0]}
            )
        else:
            context = self.continue_trace(
                parent_context, operation, {"operation_type": operation.split("_")[0]}
            )

        # Add some common attributes
        context.set_attribute("duration_target_ms", duration_ms)

        # Simulate the operation
        start_ms = time.time() * 1000

        try:
            # Simulate the operation
            await asyncio.sleep(duration_ms / 1000)  # Convert to seconds

            # Add some events
            context.add_event("operation_started")

            # 10% chance of an error
            if random.random() < 0.1:
                error_type = random.choice(
                    [
                        "timeout",
                        "permission_denied",
                        "resource_not_found",
                        "service_unavailable",
                    ]
                )
                context.set_attribute("error", True)
                context.set_attribute("error.type", error_type)
                context.add_event("operation_failed", {"error": error_type})

                # Record an exception
                exception = Exception(f"{error_type} during {operation}")
                context.record_exception(exception)

                return False, context

            # Add some operation-specific attributes and events
            if "provision" in operation:
                resource_id = f"{self.name}-{self.region}-{uuid.uuid4()}"
                context.set_attribute("resource.id", resource_id)
                context.add_event("resource_created", {"resource.id": resource_id})

            elapsed_ms = time.time() * 1000 - start_ms
            context.set_attribute("duration_actual_ms", elapsed_ms)
            context.add_event("operation_completed", {"duration_ms": elapsed_ms})

            return True, context

        except Exception as e:
            # Record the exception
            context.record_exception(e)
            return False, context
        finally:
            # End the span
            context.end()


class MultiCloudOrchestration:
    """Simulates orchestrated operations across multiple clouds"""

    def __init__(self, environments=None):
        if environments is None:
            # Create some default environments
            self.environments = [
                CloudEnvironment("aws", "us-east-1"),
                CloudEnvironment("aws", "eu-west-1"),
                CloudEnvironment("gcp", "us-central1"),
                CloudEnvironment("azure", "eastus"),
            ]
        else:
            self.environments = environments

        # Store all traces
        self.traces = {}

    async def simulate_multi_cloud_operation(
        self, operation_type="deploy", complexity=1
    ):
        """
        Simulate a complex multi-cloud operation

        Args:
            operation_type: Type of operation ("deploy", "update", "delete")
            complexity: Complexity factor (1-5) affecting the number of sub-operations

        Returns:
            Tuple of (success, root_context)
        """
        # Choose a primary environment
        primary_env = random.choice(self.environments)

        # Start the root span
        root_context = primary_env.start_trace(
            f"{operation_type}_multi_cloud",
            {"operation.type": operation_type, "complexity": complexity},
        )

        try:
            # Add the trace to our collection
            self.traces[root_context.trace_id] = []

            # Number of operations depends on complexity
            num_operations = max(
                1, int(random.normalvariate(complexity * 3, complexity))
            )

            # Distribution across clouds depends on complexity too
            num_clouds = min(len(self.environments), 1 + complexity // 2)
            selected_environments = random.sample(self.environments, num_clouds)

            root_context.set_attribute("num_operations", num_operations)
            root_context.set_attribute("num_clouds", num_clouds)

            # Create subtasks based on operation type
            sub_operations = []

            if operation_type == "deploy":
                # For deploy, we need infrastructure components
                for i in range(num_operations):
                    sub_op = random.choice(
                        ["provision_vm", "provision_storage", "provision_network"]
                    )
                    env = random.choice(selected_environments)
                    sub_operations.append((sub_op, env))

            elif operation_type == "update":
                # For update, we update existing resources
                for i in range(num_operations):
                    sub_op = "update_resource"
                    env = random.choice(selected_environments)
                    sub_operations.append((sub_op, env))

            elif operation_type == "delete":
                # For delete, we remove resources
                for i in range(num_operations):
                    sub_op = "delete_resource"
                    env = random.choice(selected_environments)
                    sub_operations.append((sub_op, env))

            else:
                # Generic operations
                for i in range(num_operations):
                    sub_op = random.choice(
                        [
                            "provision_vm",
                            "provision_storage",
                            "provision_network",
                            "query_resources",
                            "update_resource",
                            "delete_resource",
                        ]
                    )
                    env = random.choice(selected_environments)
                    sub_operations.append((sub_op, env))

            # Execute subtasks
            results = []
            for sub_op, env in sub_operations:
                # 80% of operations are executed serially
                if random.random() < 0.8:
                    root_context.add_event(
                        "sub_operation_start",
                        {"operation": sub_op, "cloud": env.name, "region": env.region},
                    )

                    success, context = await env.simulate_operation(
                        parent_context=root_context, operation=sub_op
                    )

                    root_context.add_event(
                        "sub_operation_complete",
                        {"operation": sub_op, "success": success},
                    )

                    results.append(success)

                    # If a critical operation fails, we might stop
                    if not success and random.random() < 0.3:
                        root_context.add_event(
                            "operation_aborted",
                            {
                                "reason": "critical_sub_operation_failed",
                                "operation": sub_op,
                            },
                        )
                        break

            # Check overall success
            overall_success = all(results) if results else False
            root_context.set_attribute("success", overall_success)

            if overall_success:
                root_context.add_event("operation_successful")
            else:
                root_context.add_event("operation_failed")

            # Collect all spans from all environments for this trace
            for env in self.environments:
                if root_context.trace_id in env.trace_contexts:
                    self.traces[root_context.trace_id].extend(
                        env.trace_contexts[root_context.trace_id]
                    )

            return overall_success, root_context

        except Exception as e:
            # Record the exception
            root_context.record_exception(e)
            return False, root_context
        finally:
            # End the span
            root_context.end()

    def get_trace(self, trace_id):
        """Get all spans for a given trace"""
        return self.traces.get(trace_id, [])

    def get_all_traces(self):
        """Get all traces"""
        return self.traces

    def analyze_trace_completeness(self, trace_id):
        """
        Analyze completeness of a distributed trace

        Args:
            trace_id: ID of the trace to analyze

        Returns:
            Dictionary with analysis results
        """
        spans = self.get_trace(trace_id)

        if not spans:
            return {"error": "Trace not found"}

        # Build span hierarchy
        span_map = {span.span_id: span for span in spans}
        root_spans = [span for span in spans if span.parent_id is None]

        if not root_spans:
            return {"error": "No root span found"}

        # Check for spans with missing parents
        orphaned_spans = [
            span for span in spans if span.parent_id and span.parent_id not in span_map
        ]

        # Count spans per cloud/region
        spans_by_cloud = {}
        for span in spans:
            cloud = span.attributes.get("cloud", "unknown")
            if cloud not in spans_by_cloud:
                spans_by_cloud[cloud] = 0
            spans_by_cloud[cloud] += 1

        # Check for errors
        error_spans = [span for span in spans if span.attributes.get("error", False)]

        # Measure latency and boundaries
        cross_cloud_boundaries = []

        for span in spans:
            if span.parent_id and span.parent_id in span_map:
                parent = span_map[span.parent_id]
                parent_cloud = parent.attributes.get("cloud")
                span_cloud = span.attributes.get("cloud")

                if parent_cloud and span_cloud and parent_cloud != span_cloud:
                    cross_cloud_boundaries.append(
                        {
                            "parent_span": parent.name,
                            "child_span": span.name,
                            "parent_cloud": parent_cloud,
                            "child_cloud": span_cloud,
                        }
                    )

        # Calculate timing and gap analysis
        timing_gaps = []

        # Sort spans by start time
        sorted_spans = sorted(spans, key=lambda s: s.start_time)

        for i in range(1, len(sorted_spans)):
            prev_span = sorted_spans[i - 1]
            curr_span = sorted_spans[i]

            # Check for timing gaps between consecutive spans
            if prev_span.end_time and curr_span.start_time:
                gap_ns = curr_span.start_time - prev_span.end_time
                gap_ms = gap_ns / 1_000_000

                # If gap is significant (> 10ms)
                if gap_ms > 10:
                    timing_gaps.append(
                        {
                            "prev_span": prev_span.name,
                            "next_span": curr_span.name,
                            "gap_ms": gap_ms,
                            "prev_cloud": prev_span.attributes.get("cloud"),
                            "next_cloud": curr_span.attributes.get("cloud"),
                        }
                    )

        return {
            "trace_id": trace_id,
            "span_count": len(spans),
            "root_span_count": len(root_spans),
            "orphaned_span_count": len(orphaned_spans),
            "spans_by_cloud": spans_by_cloud,
            "error_count": len(error_spans),
            "cross_cloud_boundaries": cross_cloud_boundaries,
            "cross_cloud_boundary_count": len(cross_cloud_boundaries),
            "timing_gaps": timing_gaps,
            "timing_gap_count": len(timing_gaps),
        }


async def run_distributed_tracing_test(num_operations=10, complexity_range=(1, 5)):
    """
    Run a test of distributed tracing across multi-cloud environments

    Args:
        num_operations: Number of multi-cloud operations to simulate
        complexity_range: Range of complexity values

    Returns:
        Dictionary with test results
    """
    orchestrator = MultiCloudOrchestration()

    # Run operations
    operations = []
    for _ in range(num_operations):
        op_type = random.choice(["deploy", "update", "delete"])
        complexity = random.randint(*complexity_range)

        success, context = await orchestrator.simulate_multi_cloud_operation(
            op_type, complexity
        )

        operations.append(
            {
                "type": op_type,
                "complexity": complexity,
                "success": success,
                "trace_id": context.trace_id,
            }
        )

    # Analyze traces
    trace_analyses = {}
    for op in operations:
        trace_id = op["trace_id"]
        analysis = orchestrator.analyze_trace_completeness(trace_id)
        trace_analyses[trace_id] = analysis

    # Aggregate results
    total_spans = sum(analysis["span_count"] for analysis in trace_analyses.values())
    orphaned_spans = sum(
        analysis["orphaned_span_count"] for analysis in trace_analyses.values()
    )
    cross_cloud_boundaries = sum(
        analysis["cross_cloud_boundary_count"] for analysis in trace_analyses.values()
    )
    timing_gaps = sum(
        analysis["timing_gap_count"] for analysis in trace_analyses.values()
    )

    # Calculate completeness metrics
    orphaned_span_rate = orphaned_spans / total_spans if total_spans > 0 else 0
    completeness_score = 1.0 - orphaned_span_rate

    return {
        "num_operations": num_operations,
        "total_traces": len(operations),
        "total_spans": total_spans,
        "orphaned_spans": orphaned_spans,
        "orphaned_span_rate": orphaned_span_rate,
        "completeness_score": completeness_score,
        "cross_cloud_boundaries": cross_cloud_boundaries,
        "timing_gaps": timing_gaps,
        "operations": operations,
        "trace_analyses": trace_analyses,
    }


async def main():
    """Run the distributed tracing test suite"""
    logger.info("Starting distributed tracing test")

    # Set up OpenTelemetry (when available)
    provider = TracerProvider()
    processor = SimpleSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    logger.info("OpenTelemetry configured with ConsoleSpanExporter")

    # Run tests with different complexity levels
    test_configs = [
        {"complexity": (1, 2), "operations": 5, "name": "Low complexity"},
        {"complexity": (2, 4), "operations": 5, "name": "Medium complexity"},
        {"complexity": (4, 5), "operations": 5, "name": "High complexity"},
    ]

    results = {}

    for config in test_configs:
        logger.info(f"Running test: {config['name']}")
        result = await run_distributed_tracing_test(
            num_operations=config["operations"], complexity_range=config["complexity"]
        )
        results[config["name"]] = result

    # Print summary
    print("\nDistributed Tracing Test Results:")
    print("================================")

    for name, result in results.items():
        print(f"\n{name}:")
        print(f"  Operations: {result['num_operations']}")
        print(f"  Total spans: {result['total_spans']}")
        print(f"  Completeness score: {result['completeness_score']:.2%}")
        print(f"  Cross-cloud boundaries: {result['cross_cloud_boundaries']}")
        print(f"  Timing gaps detected: {result['timing_gaps']}")

    # Determine which complexity level had the best trace completeness
    best_completeness = max(results.items(), key=lambda x: x[1]["completeness_score"])

    print(
        f"\nBest trace completeness: {best_completeness[0]} ({best_completeness[1]['completeness_score']:.2%})"
    )

    # Determine which complexity level had the most cross-cloud communication
    if any(result["cross_cloud_boundaries"] > 0 for result in results.values()):
        most_cross_cloud = max(
            results.items(), key=lambda x: x[1]["cross_cloud_boundaries"]
        )
        print(
            f"Most cross-cloud communication: {most_cross_cloud[0]} "
            f"({most_cross_cloud[1]['cross_cloud_boundaries']} boundaries)"
        )

    # Save detailed results to file
    with open("distributed_tracing_results.json", "w") as f:
        # We need to convert TraceContext objects to dictionaries
        serializable_results = {}
        for name, result in results.items():
            # Remove non-serializable objects
            serializable_result = {
                k: v
                for k, v in result.items()
                if k not in ["operations", "trace_analyses"]
            }
            serializable_results[name] = serializable_result

        json.dump(serializable_results, f, indent=2)

    print("\nDetailed results saved to distributed_tracing_results.json")


if __name__ == "__main__":
    asyncio.run(main())
