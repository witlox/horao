#!/usr/bin/env python3
"""
Test Case: Container Optimization Evaluation
Objective: Analyze and optimize containerization approaches for Python applications
"""

import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DockerAnalyzer:
    """Analyzes Docker images and builds"""

    def __init__(self, dockerfile_path: str = None, image_name: str = None):
        """
        Initialize Docker analyzer

        Args:
            dockerfile_path: Path to Dockerfile to analyze
            image_name: Name of Docker image to analyze
        """
        self.dockerfile_path = dockerfile_path
        self.image_name = image_name or "horao:test"
        self.build_logs = []
        self.image_stats = {}
        self.layer_analysis = {}

    def analyze_dockerfile(self) -> Dict:
        """
        Analyze Dockerfile structure and identify optimization opportunities

        Returns:
            Dictionary with analysis results
        """
        if not self.dockerfile_path or not os.path.exists(self.dockerfile_path):
            return {"error": "Dockerfile not found"}

        logger.info(f"Analyzing Dockerfile: {self.dockerfile_path}")

        with open(self.dockerfile_path, "r") as f:
            dockerfile_content = f.read()

        # Parse Dockerfile directives
        base_image_match = re.search(r"FROM\s+([^\s]+)", dockerfile_content)
        base_image = base_image_match.group(1) if base_image_match else "unknown"

        # Count directives
        run_commands = len(re.findall(r"^\s*RUN\s+", dockerfile_content, re.MULTILINE))
        copy_commands = len(
            re.findall(r"^\s*COPY\s+", dockerfile_content, re.MULTILINE)
        )
        add_commands = len(re.findall(r"^\s*ADD\s+", dockerfile_content, re.MULTILINE))

        # Look for multi-stage builds
        is_multi_stage = (
            len(re.findall(r"^\s*FROM\s+", dockerfile_content, re.MULTILINE)) > 1
        )

        # Check for best practices
        has_apt_cleanup = (
            "apt-get clean" in dockerfile_content
            or "apt-get autoclean" in dockerfile_content
        )
        has_pip_no_cache = "--no-cache-dir" in dockerfile_content
        has_layer_combination = "&&" in dockerfile_content
        has_non_root_user = "USER " in dockerfile_content and "root" not in re.findall(
            r"^\s*USER\s+([^\s]+)", dockerfile_content, re.MULTILINE
        )

        # Calculate optimization score (0-100)
        score = 0
        max_score = 100

        if is_multi_stage:
            score += 20

        if has_apt_cleanup:
            score += 10

        if has_pip_no_cache:
            score += 10

        if has_layer_combination:
            score += 20

        if has_non_root_user:
            score += 15

        # Reduce score for excessive commands
        score -= min(
            25, max(0, run_commands - 3) * 5
        )  # Penalize more than 3 RUN commands
        score -= min(10, add_commands * 5)  # Penalize ADD commands (prefer COPY)

        # Ensure score is within range
        score = max(0, min(100, score))

        # Generate recommendations
        recommendations = []

        if not is_multi_stage:
            recommendations.append(
                "Implement multi-stage builds to reduce final image size"
            )

        if not has_apt_cleanup:
            recommendations.append(
                "Add 'apt-get clean' after package installations to reduce layer size"
            )

        if not has_pip_no_cache:
            recommendations.append(
                "Use 'pip install --no-cache-dir' to avoid caching pip packages in layers"
            )

        if not has_layer_combination and run_commands > 3:
            recommendations.append(
                "Combine RUN commands using '&&' to reduce layer count"
            )

        if not has_non_root_user:
            recommendations.append("Switch to a non-root user for improved security")

        if base_image.startswith("python:") and not base_image.endswith(
            ("-slim", "-alpine")
        ):
            recommendations.append(
                "Consider using a smaller base image like python:3.x-slim or python:3.x-alpine"
            )

        if "requirements.txt" in dockerfile_content and "poetry" in dockerfile_content:
            recommendations.append(
                "Consider using either requirements.txt or poetry for dependency management, not both"
            )

        return {
            "base_image": base_image,
            "is_multi_stage": is_multi_stage,
            "directive_counts": {
                "run": run_commands,
                "copy": copy_commands,
                "add": add_commands,
            },
            "best_practices": {
                "has_apt_cleanup": has_apt_cleanup,
                "has_pip_no_cache": has_pip_no_cache,
                "has_layer_combination": has_layer_combination,
                "has_non_root_user": has_non_root_user,
            },
            "optimization_score": score,
            "recommendations": recommendations,
        }

    def build_image(self, context_path: str = ".", args: Dict[str, str] = None) -> bool:
        """
        Build Docker image from Dockerfile

        Args:
            context_path: Path to build context
            args: Build arguments

        Returns:
            True if build succeeds, False otherwise
        """
        if not self.dockerfile_path or not os.path.exists(self.dockerfile_path):
            logger.error("Dockerfile not found")
            return False

        logger.info(f"Building Docker image from {self.dockerfile_path}")

        # Prepare build command
        build_cmd = [
            "docker",
            "build",
            "-t",
            self.image_name,
            "-f",
            self.dockerfile_path,
        ]

        # Add build args
        if args:
            for key, value in args.items():
                build_cmd.extend(["--build-arg", f"{key}={value}"])

        # Add context path
        build_cmd.append(context_path)

        try:
            # Execute build
            start_time = time.time()
            process = subprocess.Popen(
                build_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )

            # Capture logs
            self.build_logs = []
            for line in process.stdout:
                self.build_logs.append(line.strip())
                logger.debug(line.strip())

            # Wait for process to finish
            process.wait()
            build_time = time.time() - start_time

            # Check if build succeeded
            if process.returncode == 0:
                logger.info(f"Docker build completed successfully in {build_time:.2f}s")
                self.image_stats["build_time"] = build_time
                return True
            else:
                logger.error(f"Docker build failed with exit code {process.returncode}")
                return False

        except Exception as e:
            logger.error(f"Error building Docker image: {e}")
            return False

    def analyze_image_size(self) -> Dict:
        """
        Analyze Docker image size and layers

        Returns:
            Dictionary with size analysis
        """
        logger.info(f"Analyzing Docker image: {self.image_name}")

        try:
            # Get image details
            process = subprocess.run(
                ["docker", "image", "inspect", self.image_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )

            if process.returncode != 0:
                logger.error(f"Error inspecting image: {process.stderr}")
                return {"error": "Image not found or cannot be inspected"}

            # Parse JSON output
            image_info = json.loads(process.stdout)

            # Get image size
            image_size_bytes = image_info[0].get("Size", 0)
            image_size_mb = image_size_bytes / (1024 * 1024)

            # Get layer information
            layers = image_info[0].get("RootFS", {}).get("Layers", [])
            layer_count = len(layers)

            # Get created date
            created = image_info[0].get("Created", "")

            # Store results
            self.image_stats.update(
                {
                    "size_bytes": image_size_bytes,
                    "size_mb": image_size_mb,
                    "layer_count": layer_count,
                    "created": created,
                }
            )

            return {
                "image_name": self.image_name,
                "size_mb": image_size_mb,
                "layer_count": layer_count,
                "created": created,
            }

        except Exception as e:
            logger.error(f"Error analyzing image size: {e}")
            return {"error": str(e)}

    def analyze_layers(self) -> Dict:
        """
        Analyze Docker image layers

        Returns:
            Dictionary with layer analysis
        """
        logger.info(f"Analyzing Docker image layers: {self.image_name}")

        try:
            # Get layer history
            process = subprocess.run(
                [
                    "docker",
                    "history",
                    "--no-trunc",
                    "--format",
                    "{{.Size}}|{{.CreatedBy}}|{{.Comment}}",
                    self.image_name,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )

            if process.returncode != 0:
                logger.error(f"Error getting image history: {process.stderr}")
                return {"error": "Cannot get image history"}

            # Parse layers
            layers = []
            total_size = 0

            for line in process.stdout.strip().split("\n"):
                if not line:
                    continue

                # Parse line format: Size|CreatedBy|Comment
                parts = line.split("|")
                if len(parts) >= 2:
                    size_str = parts[0].strip()
                    command = parts[1].strip()

                    # Parse size (e.g. "10.5MB", "0B")
                    try:
                        if size_str.endswith("B"):
                            size_bytes = 0  # Empty layer
                        elif size_str.endswith("kB"):
                            size_bytes = float(size_str[:-2]) * 1024
                        elif size_str.endswith("MB"):
                            size_bytes = float(size_str[:-2]) * 1024 * 1024
                        elif size_str.endswith("GB"):
                            size_bytes = float(size_str[:-2]) * 1024 * 1024 * 1024
                        else:
                            size_bytes = int(size_str)
                    except ValueError:
                        size_bytes = 0

                    # Add to total size
                    total_size += size_bytes

                    # Add to layers
                    layers.append(
                        {
                            "size_bytes": size_bytes,
                            "size_mb": size_bytes / (1024 * 1024),
                            "command": command,
                        }
                    )

            # Identify large layers
            large_layers = [
                layer
                for layer in layers
                if layer["size_mb"] > 10  # Layers larger than 10MB
            ]

            # Store results
            self.layer_analysis = {
                "total_size_mb": total_size / (1024 * 1024),
                "layer_count": len(layers),
                "layers": layers,
                "large_layers": large_layers,
            }

            return self.layer_analysis

        except Exception as e:
            logger.error(f"Error analyzing image layers: {e}")
            return {"error": str(e)}

    def generate_optimization_report(self) -> Dict:
        """
        Generate comprehensive optimization report

        Returns:
            Dictionary with optimization report
        """
        logger.info("Generating optimization report")

        # Analyze Dockerfile if available
        dockerfile_analysis = {}
        if self.dockerfile_path and os.path.exists(self.dockerfile_path):
            dockerfile_analysis = self.analyze_dockerfile()

        # Analyze image if it exists
        image_analysis = {}
        try:
            # Check if image exists
            process = subprocess.run(
                ["docker", "image", "inspect", self.image_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            if process.returncode == 0:
                image_analysis = self.analyze_image_size()
                layer_analysis = self.analyze_layers()
            else:
                image_analysis = {"error": "Image not found"}
                layer_analysis = {"error": "Image not found"}

        except Exception:
            image_analysis = {"error": "Failed to analyze image"}
            layer_analysis = {"error": "Failed to analyze layers"}

        # Generate report
        report = {
            "image_name": self.image_name,
            "dockerfile_analysis": dockerfile_analysis,
            "image_analysis": image_analysis,
            "layer_analysis": layer_analysis,
            "build_stats": {"build_time": self.image_stats.get("build_time", 0)},
        }

        # Generate additional recommendations based on layer analysis
        recommendations = dockerfile_analysis.get("recommendations", [])

        if "large_layers" in layer_analysis and layer_analysis["large_layers"]:
            for layer in layer_analysis["large_layers"]:
                command = layer["command"]
                size_mb = layer["size_mb"]

                if "apt-get" in command and "install" in command:
                    recommendations.append(
                        f"Large layer ({size_mb:.1f}MB) detected for package installation. "
                        "Consider using multi-stage builds and installing only required packages."
                    )
                elif "pip install" in command:
                    recommendations.append(
                        f"Large layer ({size_mb:.1f}MB) detected for pip installation. "
                        "Consider using multi-stage builds and '--no-cache-dir'."
                    )
                elif "COPY" in command or "ADD" in command:
                    recommendations.append(
                        f"Large layer ({size_mb:.1f}MB) detected for file copying. "
                        "Ensure only necessary files are copied into the image."
                    )

        report["optimization_recommendations"] = list(set(recommendations))

        return report


def create_optimized_dockerfile(original_path: str, output_path: str) -> Dict:
    """
    Create an optimized version of a Dockerfile

    Args:
        original_path: Path to original Dockerfile
        output_path: Path to write optimized Dockerfile

    Returns:
        Dictionary with optimization details
    """
    logger.info(f"Creating optimized Dockerfile from {original_path}")

    if not os.path.exists(original_path):
        return {"error": "Original Dockerfile not found"}

    with open(original_path, "r") as f:
        original_content = f.read()

    # Apply optimizations
    optimized_content = original_content

    # 1. Replace full Python image with slim version
    optimized_content = re.sub(
        r"FROM python:(\d+\.\d+)(?!-slim|-alpine)",
        r"FROM python:\1-slim",
        optimized_content,
    )

    # 2. Add apt-get cleanup if missing
    if "apt-get" in optimized_content and "apt-get clean" not in optimized_content:
        optimized_content = re.sub(
            r"(apt-get\s+\w+\s+.*?)(?=\n\s*[A-Z])",
            r"\1 && apt-get clean && rm -rf /var/lib/apt/lists/*",
            optimized_content,
        )

    # 3. Add --no-cache-dir to pip commands if missing
    if "pip install" in optimized_content and "--no-cache-dir" not in optimized_content:
        optimized_content = re.sub(
            r"pip install", r"pip install --no-cache-dir", optimized_content
        )

    # 4. Combine multiple RUN commands
    run_commands = re.findall(r"^RUN\s+(.+)$", optimized_content, re.MULTILINE)
    if len(run_commands) > 3:
        # Combine apt-get commands
        apt_get_commands = [cmd for cmd in run_commands if "apt-get" in cmd]
        if len(apt_get_commands) > 1:
            combined_apt = " && ".join(apt_get_commands)
            for cmd in apt_get_commands:
                optimized_content = optimized_content.replace(f"RUN {cmd}", "", 1)
            optimized_content = optimized_content.replace(
                "FROM", f"FROM\n\nRUN {combined_apt}\n", 1
            )

        # Combine pip commands
        pip_commands = [
            cmd
            for cmd in run_commands
            if "pip install" in cmd and cmd not in apt_get_commands
        ]
        if len(pip_commands) > 1:
            combined_pip = " && ".join(pip_commands)
            for cmd in pip_commands:
                optimized_content = optimized_content.replace(f"RUN {cmd}", "", 1)
            optimized_content = re.sub(r"\n\n+", "\n\n", optimized_content)
            optimized_content += f"\n\nRUN {combined_pip}\n"

    # 5. Add non-root user if missing
    if "USER " not in optimized_content:
        user_content = "\n# Create and use non-root user\n"
        user_content += "RUN adduser --disabled-password --gecos '' appuser\n"
        user_content += "USER appuser\n"

        # Add before CMD or at the end if no CMD
        if "CMD " in optimized_content:
            optimized_content = optimized_content.replace(
                "CMD ", f"{user_content}\nCMD ", 1
            )
        else:
            optimized_content += f"{user_content}\n"

    # Write optimized Dockerfile
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(optimized_content)

    return {
        "original_path": original_path,
        "optimized_path": output_path,
        "original_size": len(original_content),
        "optimized_size": len(optimized_content),
        "optimizations_applied": {
            "slim_base_image": "FROM python:" in original_content
            and "-slim" not in original_content,
            "apt_get_cleanup_added": "apt-get" in original_content
            and "apt-get clean" not in original_content,
            "pip_no_cache_added": "pip install" in original_content
            and "--no-cache-dir" not in original_content,
            "combined_run_commands": len(run_commands) > 3,
            "non_root_user_added": "USER " not in original_content,
        },
    }


def compare_docker_builds(original_dockerfile: str, optimized_dockerfile: str) -> Dict:
    """
    Compare original and optimized Docker builds

    Args:
        original_dockerfile: Path to original Dockerfile
        optimized_dockerfile: Path to optimized Dockerfile

    Returns:
        Dictionary with comparison results
    """
    logger.info("Comparing Docker builds")

    results = {"original": {}, "optimized": {}, "comparison": {}}

    # Analyze original Dockerfile
    original_analyzer = DockerAnalyzer(original_dockerfile, "horao:original")
    original_analysis = original_analyzer.analyze_dockerfile()

    # Build original image
    original_build_success = original_analyzer.build_image()
    if original_build_success:
        original_analyzer.analyze_image_size()
        original_analyzer.analyze_layers()

    # Analyze optimized Dockerfile
    optimized_analyzer = DockerAnalyzer(optimized_dockerfile, "horao:optimized")
    optimized_analysis = optimized_analyzer.analyze_dockerfile()

    # Build optimized image
    optimized_build_success = optimized_analyzer.build_image()
    if optimized_build_success:
        optimized_analyzer.analyze_image_size()
        optimized_analyzer.analyze_layers()

    # Store results
    results["original"] = {
        "dockerfile_analysis": original_analysis,
        "build_success": original_build_success,
        "image_stats": original_analyzer.image_stats,
        "layer_analysis": original_analyzer.layer_analysis,
    }

    results["optimized"] = {
        "dockerfile_analysis": optimized_analysis,
        "build_success": optimized_build_success,
        "image_stats": optimized_analyzer.image_stats,
        "layer_analysis": optimized_analyzer.layer_analysis,
    }

    # Calculate improvements
    if original_build_success and optimized_build_success:
        original_size = original_analyzer.image_stats.get("size_mb", 0)
        optimized_size = optimized_analyzer.image_stats.get("size_mb", 0)

        original_layers = original_analyzer.image_stats.get("layer_count", 0)
        optimized_layers = optimized_analyzer.image_stats.get("layer_count", 0)

        original_build_time = original_analyzer.image_stats.get("build_time", 0)
        optimized_build_time = optimized_analyzer.image_stats.get("build_time", 0)

        size_reduction = original_size - optimized_size
        size_reduction_percent = (
            (size_reduction / original_size) * 100 if original_size > 0 else 0
        )

        layer_reduction = original_layers - optimized_layers
        layer_reduction_percent = (
            (layer_reduction / original_layers) * 100 if original_layers > 0 else 0
        )

        build_time_diff = original_build_time - optimized_build_time
        build_time_diff_percent = (
            (build_time_diff / original_build_time) * 100
            if original_build_time > 0
            else 0
        )

        results["comparison"] = {
            "size_reduction_mb": size_reduction,
            "size_reduction_percent": size_reduction_percent,
            "layer_reduction": layer_reduction,
            "layer_reduction_percent": layer_reduction_percent,
            "build_time_diff_seconds": build_time_diff,
            "build_time_diff_percent": build_time_diff_percent,
        }

    return results


def main():
    """Run container optimization tests and generate report"""
    logger.info("Starting Container Optimization Tests")

    # Check for Docker
    try:
        subprocess.run(["docker", "--version"], check=True, stdout=subprocess.PIPE)
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error(
            "Docker not found or not running. Please install Docker and try again."
        )
        return 1

    # Find Dockerfile in project root
    project_root = Path(__file__).parent.parent.parent
    dockerfile_path = project_root / "Dockerfile"

    if not dockerfile_path.exists():
        logger.error(f"Dockerfile not found at {dockerfile_path}")
        return 1

    print("\nContainer Optimization Analysis")
    print("==============================\n")

    print(f"Analyzing Dockerfile: {dockerfile_path}")

    # Analyze original Dockerfile
    analyzer = DockerAnalyzer(str(dockerfile_path))
    report = analyzer.generate_optimization_report()

    # Print report summary
    print("\nDockerfile Analysis:")
    print(f"  Base Image: {report['dockerfile_analysis'].get('base_image', 'unknown')}")
    print(
        f"  Optimization Score: {report['dockerfile_analysis'].get('optimization_score', 0)}/100"
    )

    print("\nOptimization Recommendations:")
    for i, rec in enumerate(report["optimization_recommendations"], 1):
        print(f"  {i}. {rec}")

    # Create optimized Dockerfile
    optimized_path = (
        project_root / "research" / "devops_practices" / "Dockerfile.optimized"
    )
    optimization_result = create_optimized_dockerfile(
        str(dockerfile_path), str(optimized_path)
    )

    if "error" in optimization_result:
        logger.error(
            f"Error creating optimized Dockerfile: {optimization_result['error']}"
        )
        return 1

    print(f"\nOptimized Dockerfile created at: {optimized_path}")

    # Option to build and compare if Docker is available
    should_build = (
        input("\nBuild and compare Docker images? (y/n): ").strip().lower() == "y"
    )

    if should_build:
        print("\nBuilding and comparing Docker images...")
        comparison = compare_docker_builds(str(dockerfile_path), str(optimized_path))

        if (
            comparison["original"]["build_success"]
            and comparison["optimized"]["build_success"]
        ):

            orig_size = comparison["original"]["image_stats"]["size_mb"]
            opt_size = comparison["optimized"]["image_stats"]["size_mb"]
            size_reduction_pct = comparison["comparison"]["size_reduction_percent"]

            print("\nComparison Results:")
            print(f"  Original Image Size: {orig_size:.2f}MB")
            print(f"  Optimized Image Size: {opt_size:.2f}MB")
            print(f"  Size Reduction: {size_reduction_pct:.2f}%")

            # Save detailed report
            report_path = (
                project_root
                / "research"
                / "devops_practices"
                / "container_optimization_report.json"
            )
            with open(report_path, "w") as f:
                json.dump(comparison, f, indent=2)

            print(f"\nDetailed comparison report saved to: {report_path}")
        else:
            if not comparison["original"]["build_success"]:
                print("\nError: Failed to build original Docker image")
            if not comparison["optimized"]["build_success"]:
                print("\nError: Failed to build optimized Docker image")

    return 0


if __name__ == "__main__":
    sys.exit(main())
