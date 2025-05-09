#!/usr/bin/env python3
"""
Test Case: Telemetry Sampling Strategies
Objective: Evaluate different sampling approaches for telemetry data
"""

import asyncio
import json
import logging
import random
import sys
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import numpy as np  # type: ignore

# Add project root to path so we can import HORAO modules
sys.path.append(str(Path(__file__).parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Event:
    """Represents a telemetry event for sampling testing"""

    def __init__(
        self,
        event_type: str,
        timestamp: float = None,
        attributes: Dict = None,
        severity: str = "info",
    ):
        """
        Initialize a telemetry event

        Args:
            event_type: Type of event (e.g., "request", "resource.created")
            timestamp: Event timestamp (defaults to current time)
            attributes: Event attributes
            severity: Event severity level
        """
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.timestamp = timestamp or time.time()
        self.attributes = attributes or {}
        self.severity = severity

        # Add some common attributes
        if "service" not in self.attributes:
            self.attributes["service"] = random.choice(
                ["api", "controller", "scheduler", "resource-manager"]
            )

        if "cloud" not in self.attributes:
            self.attributes["cloud"] = random.choice(["aws", "gcp", "azure"])

        if "region" not in self.attributes:
            regions = {
                "aws": ["us-east-1", "us-west-2", "eu-west-1"],
                "gcp": ["us-central1", "us-east4", "europe-west1"],
                "azure": ["eastus", "westus2", "westeurope"],
            }
            self.attributes["region"] = random.choice(
                regions.get(self.attributes["cloud"], ["unknown"])
            )

        # Add latency for request events
        if event_type == "request" and "latency_ms" not in self.attributes:
            # Log-normal distribution for more realistic latency values
            self.attributes["latency_ms"] = random.lognormvariate(3, 1)

            # Add status code
            self.attributes["status_code"] = random.choices(
                [200, 400, 500], weights=[0.9, 0.05, 0.05], k=1
            )[0]

            # Make 5xx errors critical severity
            if self.attributes["status_code"] >= 500:
                self.severity = "critical"
            # Make 4xx errors warning severity
            elif self.attributes["status_code"] >= 400:
                self.severity = "warning"

        # For resource events, add resource type
        if "resource" in event_type and "resource.type" not in self.attributes:
            self.attributes["resource.type"] = random.choice(
                ["vm", "storage", "network", "container", "function"]
            )

    def to_dict(self) -> Dict:
        """Convert event to dictionary"""
        return {
            "id": self.event_id,
            "type": self.event_type,
            "timestamp": self.timestamp,
            "attributes": self.attributes,
            "severity": self.severity,
        }


class SamplingStrategy:
    """Base class for telemetry sampling strategies"""

    def __init__(self, name: str):
        """Initialize sampling strategy"""
        self.name = name

    def should_sample(self, event: Event) -> bool:
        """
        Determine if an event should be sampled

        Args:
            event: The event to evaluate

        Returns:
            True if the event should be sampled, False otherwise
        """
        raise NotImplementedError("Sampling strategy not implemented")

    def get_info(self) -> Dict:
        """Get information about the sampling strategy"""
        return {"name": self.name}


class RandomSamplingStrategy(SamplingStrategy):
    """Simple random sampling strategy with a fixed rate"""

    def __init__(self, sample_rate: float = 0.1):
        """
        Initialize random sampling strategy

        Args:
            sample_rate: Percentage of events to sample (0.0-1.0)
        """
        super().__init__(f"random_{int(sample_rate * 100)}pct")
        self.sample_rate = sample_rate

    def should_sample(self, event: Event) -> bool:
        """Sample events randomly based on the sample rate"""
        return random.random() < self.sample_rate

    def get_info(self) -> Dict:
        """Get information about the sampling strategy"""
        info = super().get_info()
        info["sample_rate"] = self.sample_rate
        return info


class PrioritySamplingStrategy(SamplingStrategy):
    """Samples events based on their priority (severity)"""

    def __init__(self, priority_rates: Dict[str, float] = None):
        """
        Initialize priority sampling strategy

        Args:
            priority_rates: Dictionary mapping severity levels to sampling rates
                           e.g., {"critical": 1.0, "error": 0.8, "warning": 0.5, "info": 0.1}
        """
        super().__init__("priority")

        self.priority_rates = priority_rates or {
            "critical": 1.0,  # Always sample critical events
            "error": 0.8,  # Sample 80% of errors
            "warning": 0.2,  # Sample 20% of warnings
            "info": 0.05,  # Sample 5% of info events
        }

    def should_sample(self, event: Event) -> bool:
        """Sample based on event severity"""
        rate = self.priority_rates.get(
            event.severity, 0.01
        )  # Default to 1% for unknown severities
        return random.random() < rate

    def get_info(self) -> Dict:
        """Get information about the sampling strategy"""
        info = super().get_info()
        info["priority_rates"] = self.priority_rates
        return info


class AdaptiveSamplingStrategy(SamplingStrategy):
    """Dynamically adjusts sampling rate based on traffic volume"""

    def __init__(
        self,
        target_samples_per_second: float = 100,
        min_sampling_rate: float = 0.01,
        max_sampling_rate: float = 1.0,
    ):
        """
        Initialize adaptive sampling strategy

        Args:
            target_samples_per_second: Target number of samples per second
            min_sampling_rate: Minimum sampling rate (0.0-1.0)
            max_sampling_rate: Maximum sampling rate (0.0-1.0)
        """
        super().__init__("adaptive")
        self.target_samples_per_second = target_samples_per_second
        self.min_sampling_rate = min_sampling_rate
        self.max_sampling_rate = max_sampling_rate

        # Track recent event rates
        self.current_sampling_rate = 0.1  # Start at 10%
        self.event_count = 0
        self.sample_count = 0
        self.last_adjustment_time = time.time()
        self.window_size_seconds = 5  # Adjust every 5 seconds

    def should_sample(self, event: Event) -> bool:
        """
        Determine if event should be sampled, and adjust rate if needed

        This implementation uses a token bucket approach for rate limiting,
        but also adjusts the sampling rate periodically based on observed traffic.
        """
        # Count this event
        self.event_count += 1

        # Apply current sampling rate
        sampled = random.random() < self.current_sampling_rate

        if sampled:
            self.sample_count += 1

        # Periodically adjust the sampling rate based on observed traffic
        current_time = time.time()
        elapsed_seconds = current_time - self.last_adjustment_time

        if elapsed_seconds >= self.window_size_seconds and self.event_count > 0:
            # Calculate events per second
            events_per_second = self.event_count / elapsed_seconds

            if events_per_second > 0:
                # Calculate ideal sampling rate
                ideal_rate = self.target_samples_per_second / events_per_second

                # Constrain to min/max
                self.current_sampling_rate = max(
                    self.min_sampling_rate, min(self.max_sampling_rate, ideal_rate)
                )

            # Reset counters
            self.event_count = 0
            self.sample_count = 0
            self.last_adjustment_time = current_time

        return sampled

    def get_info(self) -> Dict:
        """Get information about the sampling strategy"""
        info = super().get_info()
        info.update(
            {
                "target_samples_per_second": self.target_samples_per_second,
                "min_sampling_rate": self.min_sampling_rate,
                "max_sampling_rate": self.max_sampling_rate,
                "current_sampling_rate": self.current_sampling_rate,
            }
        )
        return info


class TailSamplingStrategy(SamplingStrategy):
    """
    Samples events based on their importance post-collection
    This is a simplified implementation of tail sampling
    """

    def __init__(
        self,
        buffer_time_seconds: float = 30,
        error_threshold_pct: float = 5.0,
        latency_threshold_ms: float = 1000,
    ):
        """
        Initialize tail sampling strategy

        Args:
            buffer_time_seconds: How long to buffer events before making sampling decisions
            error_threshold_pct: Error percentage threshold for sampling a service (%)
            latency_threshold_ms: Latency threshold for sampling a service (ms)
        """
        super().__init__("tail")
        self.buffer_time_seconds = buffer_time_seconds
        self.error_threshold_pct = error_threshold_pct
        self.latency_threshold_ms = latency_threshold_ms

        # Service stats for decision making
        self.service_stats = defaultdict(
            lambda: {
                "request_count": 0,
                "error_count": 0,
                "total_latency_ms": 0,
                "max_latency_ms": 0,
            }
        )

        # Buffered events for processing
        self.event_buffer = []
        self.last_process_time = time.time()

    def should_sample(self, event: Event) -> bool:
        """
        Buffer the event and make sampling decisions periodically

        In a real implementation, this would be more complex with a
        background processor, but for testing we simplify.
        """
        current_time = time.time()

        # Add event to buffer
        self.event_buffer.append(event)

        # Update stats for service metrics
        service = event.attributes.get("service")
        if service and event.event_type == "request":
            stats = self.service_stats[service]
            stats["request_count"] += 1

            # Track errors
            if event.attributes.get("status_code", 200) >= 400:
                stats["error_count"] += 1

            # Track latency
            latency = event.attributes.get("latency_ms", 0)
            if latency > 0:
                stats["total_latency_ms"] += latency
                stats["max_latency_ms"] = max(stats["max_latency_ms"], latency)

        # Process buffer if enough time has elapsed
        if current_time - self.last_process_time >= self.buffer_time_seconds:
            return self._process_buffered_event(event)

        # By default, sample everything until we process the buffer
        return True

    def _process_buffered_event(self, event: Event) -> bool:
        """Process the current buffer and make sampling decisions"""
        # Calculate service metrics
        problematic_services = set()

        for service, stats in self.service_stats.items():
            if stats["request_count"] > 0:
                error_rate = (stats["error_count"] / stats["request_count"]) * 100
                avg_latency = stats["total_latency_ms"] / stats["request_count"]

                # Identify problematic services
                if (
                    error_rate >= self.error_threshold_pct
                    or avg_latency >= self.latency_threshold_ms
                    or stats["max_latency_ms"] >= self.latency_threshold_ms * 2
                ):
                    problematic_services.add(service)

        # Always sample events from problematic services
        if event.attributes.get("service") in problematic_services:
            return True

        # Always sample error/critical events
        if event.severity in ("error", "critical"):
            return True

        # Sample 20% of warning events
        if event.severity == "warning":
            return random.random() < 0.2

        # Sample 5% of normal events from non-problematic services
        return random.random() < 0.05

    def get_info(self) -> Dict:
        """Get information about the sampling strategy"""
        info = super().get_info()
        info.update(
            {
                "buffer_time_seconds": self.buffer_time_seconds,
                "error_threshold_pct": self.error_threshold_pct,
                "latency_threshold_ms": self.latency_threshold_ms,
            }
        )
        return info


class SamplingEvaluator:
    """Evaluates and compares different sampling strategies"""

    def __init__(self, strategies: List[SamplingStrategy]):
        """
        Initialize the evaluator

        Args:
            strategies: List of sampling strategies to evaluate
        """
        self.strategies = strategies
        self.results = {
            strategy.name: {
                "strategy": strategy,
                "events_seen": 0,
                "events_sampled": 0,
                "sampled_by_type": defaultdict(int),
                "sampled_by_severity": defaultdict(int),
                "sampled_by_service": defaultdict(int),
                "important_events_seen": 0,
                "important_events_sampled": 0,
                "sampled_latencies": [],
            }
            for strategy in strategies
        }

    def process_event(self, event: Event):
        """
        Process an event through all sampling strategies

        Args:
            event: The event to process
        """
        # Check if event is "important" (errors, high latency)
        is_important = (
            event.severity in ("critical", "error")
            or event.attributes.get("status_code", 200) >= 400
            or event.attributes.get("latency_ms", 0) >= 1000
        )

        for strategy in self.strategies:
            result = self.results[strategy.name]
            result["events_seen"] += 1

            if is_important:
                result["important_events_seen"] += 1

            # Check if this event should be sampled
            if strategy.should_sample(event):
                result["events_sampled"] += 1
                result["sampled_by_type"][event.event_type] += 1
                result["sampled_by_severity"][event.severity] += 1
                result["sampled_by_service"][
                    event.attributes.get("service", "unknown")
                ] += 1

                if "latency_ms" in event.attributes:
                    result["sampled_latencies"].append(event.attributes["latency_ms"])

                if is_important:
                    result["important_events_sampled"] += 1

    def get_results(self) -> Dict:
        """
        Get evaluation results

        Returns:
            Dictionary with results
        """
        for name, result in self.results.items():
            # Calculate sampling percentages
            if result["events_seen"] > 0:
                result["sampling_rate"] = (
                    result["events_sampled"] / result["events_seen"]
                )
            else:
                result["sampling_rate"] = 0

            # Calculate important event capture rate
            if result["important_events_seen"] > 0:
                result["important_capture_rate"] = (
                    result["important_events_sampled"] / result["important_events_seen"]
                )
            else:
                result["important_capture_rate"] = 0

            # Calculate latency statistics if available
            if result["sampled_latencies"]:
                result["latency_stats"] = {
                    "min": min(result["sampled_latencies"]),
                    "max": max(result["sampled_latencies"]),
                    "mean": np.mean(result["sampled_latencies"]),
                    "median": np.median(result["sampled_latencies"]),
                    "p90": np.percentile(result["sampled_latencies"], 90),
                    "p99": np.percentile(result["sampled_latencies"], 99),
                }
            else:
                result["latency_stats"] = {}

            # Get strategy info
            result["strategy_info"] = result["strategy"].get_info()

            # Clean up non-serializable objects for JSON output
            result.pop("strategy")
            result["sampled_by_type"] = dict(result["sampled_by_type"])
            result["sampled_by_severity"] = dict(result["sampled_by_severity"])
            result["sampled_by_service"] = dict(result["sampled_by_service"])
            result.pop("sampled_latencies")

        return self.results

    def evaluate_strategies(self) -> Dict:
        """
        Calculate effectiveness scores for each strategy

        Returns:
            Dictionary with strategy effectiveness scores
        """
        scores = {}

        for name, result in self.results.items():
            # Scoring criteria:
            # 1. Important event coverage (60% weight)
            important_score = result.get("important_capture_rate", 0) * 0.6

            # 2. Data reduction - inverse of sampling rate (20% weight)
            # (we want to minimize data while capturing important events)
            reduction_score = (1 - result.get("sampling_rate", 0)) * 0.2

            # 3. Service coverage evenness (20% weight)
            # (we want to make sure we don't under-sample specific services)
            service_counts = result.get("sampled_by_service", {})
            if service_counts:
                service_values = list(service_counts.values())
                service_mean = np.mean(service_values)
                if service_mean > 0:
                    # Calculate coefficient of variation (lower is more even)
                    service_std = np.std(service_values)
                    service_cv = service_std / service_mean
                    service_evenness = max(
                        0, 1 - service_cv
                    )  # 0 to 1, higher is better
                else:
                    service_evenness = 0
            else:
                service_evenness = 0

            service_score = service_evenness * 0.2

            # Calculate total score
            total_score = important_score + reduction_score + service_score

            scores[name] = {
                "total_score": total_score,
                "important_event_score": important_score / 0.6,  # Normalize to 0-1
                "data_reduction_score": reduction_score / 0.2,  # Normalize to 0-1
                "service_coverage_score": service_score / 0.2,  # Normalize to 0-1
            }

        return scores


async def generate_test_load(
    event_count: int, burst_factor: float = 1.0
) -> List[Event]:
    """
    Generate a test load of events with realistic patterns

    Args:
        event_count: Total number of events to generate
        burst_factor: Factor to control burstiness of events (1.0 = normal, >1 = more bursty)

    Returns:
        List of generated events
    """
    events = []

    # Event types and their relative frequencies
    event_types = {
        "request": 0.7,  # Most events are requests
        "resource.created": 0.1,  # Some resource events
        "resource.updated": 0.1,
        "resource.deleted": 0.05,
        "system.metric": 0.05,  # Fewer system metrics
    }

    # Generate timestamps with a realistic pattern (some burstiness)
    base_time = time.time() - (3600 * 2)  # Start 2 hours ago
    timestamps = []

    # Generate timestamps with bursts
    current_time = base_time
    while len(timestamps) < event_count:
        # Generate a burst of activity
        burst_size = int(
            random.expovariate(1 / 20) * burst_factor
        )  # Average burst size of 20
        burst_duration = burst_size / 10  # seconds

        for i in range(burst_size):
            if len(timestamps) < event_count:
                # Events within a burst are closely spaced
                timestamps.append(current_time + (i * burst_duration / burst_size))
            else:
                break

        # Wait until the next burst
        current_time += burst_duration + random.expovariate(
            1 / 30
        )  # Average 30s between bursts

    # Generate events with timestamps
    for i, timestamp in enumerate(timestamps):
        # Select event type based on probabilities
        event_type = random.choices(
            list(event_types.keys()), weights=list(event_types.values()), k=1
        )[0]

        # Periodically introduce an "incident" with higher error rates
        is_incident = False
        if i > 0 and i % 1000 == 0:
            is_incident = True
            incident_duration = random.randint(50, 200)  # Events affected by incident

        # Create event attributes
        attributes = {}

        # During incidents, increase error rate and latency
        if is_incident and i % 1000 < incident_duration:
            if event_type == "request":
                # Higher error rate during incidents
                attributes["status_code"] = random.choices(
                    [200, 500, 503], weights=[0.5, 0.3, 0.2], k=1
                )[0]

                # Higher latency during incidents
                attributes["latency_ms"] = random.lognormvariate(5, 1)  # Higher mean

        # Create the event
        event = Event(event_type, timestamp, attributes)
        events.append(event)

    logger.info(f"Generated {len(events)} test events")
    return events


async def main():
    """Run the sampling strategy evaluation"""
    logger.info("Starting telemetry sampling strategy evaluation")

    # Create strategies to evaluate
    strategies = [
        # Basic random sampling at different rates
        RandomSamplingStrategy(sample_rate=0.01),  # 1%
        RandomSamplingStrategy(sample_rate=0.05),  # 5%
        RandomSamplingStrategy(sample_rate=0.1),  # 10%
        RandomSamplingStrategy(sample_rate=0.2),  # 20%
        # Priority-based sampling
        PrioritySamplingStrategy(),
        # Adaptive sampling
        AdaptiveSamplingStrategy(target_samples_per_second=50),
        AdaptiveSamplingStrategy(target_samples_per_second=100),
        # Tail sampling
        TailSamplingStrategy(),
    ]

    # Create evaluator
    evaluator = SamplingEvaluator(strategies)

    # Generate test load
    events = await generate_test_load(event_count=10000, burst_factor=1.5)

    # Process events through all strategies
    for i, event in enumerate(events):
        evaluator.process_event(event)
        if i % 1000 == 0:
            logger.info(f"Processed {i} events")

    # Get results
    results = evaluator.get_results()
    scores = evaluator.evaluate_strategies()

    # Print summary
    print("\nTelemetry Sampling Strategy Evaluation Results:")
    print("==============================================")

    print("\nStrategy                 | Sampling Rate | Important Events | Score")
    print("--------------------------+--------------+------------------+------")

    for strategy in strategies:
        name = strategy.name
        result = results[name]
        score = scores[name]

        print(
            f"{name:25} | {result['sampling_rate']*100:11.2f}% | {result['important_capture_rate']*100:15.2f}% | {score['total_score']*100:5.2f}%"
        )

    # Find the best strategy
    best_strategy = max(scores.items(), key=lambda x: x[1]["total_score"])

    print(
        f"\nBest overall strategy: {best_strategy[0]} (Score: {best_strategy[1]['total_score']*100:.2f}%)"
    )

    # Find the best strategy for important event capture
    best_important = max(scores.items(), key=lambda x: x[1]["important_event_score"])
    print(
        f"Best for important events: {best_important[0]} (Capture rate: {results[best_important[0]]['important_capture_rate']*100:.2f}%)"
    )

    # Find the best strategy for data reduction
    best_reduction = max(scores.items(), key=lambda x: x[1]["data_reduction_score"])
    print(
        f"Best for data reduction: {best_reduction[0]} (Sampling rate: {results[best_reduction[0]]['sampling_rate']*100:.2f}%)"
    )

    # Save detailed results to file
    output = {
        "results": results,
        "scores": scores,
        "best_strategy": best_strategy[0],
        "best_important_event_strategy": best_important[0],
        "best_data_reduction_strategy": best_reduction[0],
    }

    with open("sampling_strategy_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\nDetailed results saved to sampling_strategy_results.json")


if __name__ == "__main__":
    asyncio.run(main())
