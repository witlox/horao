#!/usr/bin/env python3
"""
Test Case: Dependency Management Analysis
Objective: Evaluate Poetry for dependency management in distributed systems
"""

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class DependencyInfo:
    """Information about a Python dependency"""

    name: str
    version: str
    constraints: str
    is_dev: bool = False
    required_by: List[str] = None

    def __post_init__(self):
        if self.required_by is None:
            self.required_by = []


class DependencyAnalyzer:
    """Analyzes dependency management strategies"""

    def __init__(self, project_root: str):
        """
        Initialize dependency analyzer

        Args:
            project_root: Path to the project root directory
        """
        self.project_root = Path(project_root)
        self.has_poetry = self._check_poetry_file()
        self.has_requirements = self._check_requirements_file()
        self.dependencies = {}
        self.dev_dependencies = {}
        self.dependency_tree = {}

    def _check_poetry_file(self) -> bool:
        """Check if the project uses Poetry"""
        return (self.project_root / "pyproject.toml").exists()

    def _check_requirements_file(self) -> bool:
        """Check if the project uses requirements.txt"""
        return (self.project_root / "requirements.txt").exists()

    def analyze_dependencies(self) -> Dict:
        """
        Analyze project dependencies

        Returns:
            Dictionary with dependency analysis results
        """
        results = {
            "poetry_found": self.has_poetry,
            "requirements_found": self.has_requirements,
            "dependency_count": 0,
            "dev_dependency_count": 0,
            "dependencies": [],
            "dev_dependencies": [],
            "dependency_stats": {},
        }

        if self.has_poetry:
            # Parse pyproject.toml for dependencies
            poetry_deps = self._analyze_poetry_dependencies()
            results.update(poetry_deps)

        if self.has_requirements:
            # Parse requirements.txt
            req_deps = self._analyze_requirements_txt()

            # If we have both, merge the results
            if self.has_poetry:
                # Merge dependencies, with requirements.txt overriding poetry if there's a conflict
                for dep in req_deps["dependencies"]:
                    if not any(
                        d["name"] == dep["name"] for d in results["dependencies"]
                    ):
                        results["dependencies"].append(dep)

                # Update counts
                results["dependency_count"] = len(results["dependencies"])
            else:
                results.update(req_deps)

        # Calculate dependency statistics
        results["dependency_stats"] = self._calculate_dependency_stats(
            results["dependencies"]
        )

        return results

    def _analyze_poetry_dependencies(self) -> Dict:
        """
        Analyze dependencies defined in pyproject.toml

        Returns:
            Dictionary with poetry dependency information
        """
        toml_path = self.project_root / "pyproject.toml"

        if not toml_path.exists():
            return {"error": "pyproject.toml not found"}

        logger.info(f"Analyzing dependencies in {toml_path}")

        # Parse dependencies from pyproject.toml
        dependencies = []
        dev_dependencies = []

        with open(toml_path, "r") as f:
            content = f.read()

        # Extract main dependencies
        main_deps_match = re.search(
            r"\[tool\.poetry\.dependencies\](.*?)(\[|\Z)", content, re.DOTALL
        )
        if main_deps_match:
            main_deps_str = main_deps_match.group(1)
            dependencies = self._parse_toml_dependencies(main_deps_str)

        # Extract dev dependencies (may be named dev-dependencies or group.dev.dependencies)
        dev_deps_match = re.search(
            r"\[tool\.poetry\.dev-dependencies\](.*?)(\[|\Z)", content, re.DOTALL
        )
        if not dev_deps_match:
            dev_deps_match = re.search(
                r"\[tool\.poetry\.group\.dev\.dependencies\](.*?)(\[|\Z)",
                content,
                re.DOTALL,
            )

        if dev_deps_match:
            dev_deps_str = dev_deps_match.group(1)
            dev_dependencies = self._parse_toml_dependencies(dev_deps_str, is_dev=True)

        # Store for later use
        self.dependencies = {dep["name"]: dep for dep in dependencies}
        self.dev_dependencies = {dep["name"]: dep for dep in dev_dependencies}

        return {
            "dependency_count": len(dependencies),
            "dev_dependency_count": len(dev_dependencies),
            "dependencies": dependencies,
            "dev_dependencies": dev_dependencies,
        }

    def _parse_toml_dependencies(
        self, deps_str: str, is_dev: bool = False
    ) -> List[Dict]:
        """
        Parse dependencies from a TOML section string

        Args:
            deps_str: The section of the TOML file containing dependencies
            is_dev: Whether these are dev dependencies

        Returns:
            List of dependency dictionaries
        """
        deps = []

        # Look for name = "version" or name = { version = "version", ... }
        simple_deps = re.finditer(r'^(\S+)\s*=\s*"([^"]+)"', deps_str, re.MULTILINE)
        for match in simple_deps:
            name = match.group(1).strip()
            version = match.group(2).strip()

            # Skip python itself
            if name.lower() == "python":
                continue

            deps.append(
                {
                    "name": name,
                    "version": version,
                    "constraints": version,
                    "is_dev": is_dev,
                }
            )

        # Look for complex dependencies with more settings
        complex_deps = re.finditer(r"^(\S+)\s*=\s*\{([^\}]+)\}", deps_str, re.MULTILINE)
        for match in complex_deps:
            name = match.group(1).strip()
            settings = match.group(2).strip()

            # Skip python itself
            if name.lower() == "python":
                continue

            # Extract version constraint
            version_match = re.search(r'version\s*=\s*"([^"]+)"', settings)
            version = version_match.group(1) if version_match else "Not specified"

            deps.append(
                {
                    "name": name,
                    "version": version,
                    "constraints": version,
                    "is_dev": is_dev,
                }
            )

        return deps

    def _analyze_requirements_txt(self) -> Dict:
        """
        Analyze dependencies defined in requirements.txt

        Returns:
            Dictionary with requirements.txt dependency information
        """
        req_path = self.project_root / "requirements.txt"

        if not req_path.exists():
            return {"error": "requirements.txt not found"}

        logger.info(f"Analyzing dependencies in {req_path}")

        dependencies = []

        with open(req_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Handle line continuation
                if line.endswith("\\"):
                    line = line[:-1].strip()

                # Handle options like --index-url
                if line.startswith("-"):
                    continue

                # Handle -r includes
                if line.startswith("-r") or line.startswith("--requirement"):
                    # We'd need to process another file here, but keeping it simple
                    continue

                # Parse dependency specification
                # Example formats: package==1.0.0, package>=1.0.0, package~=1.0.0
                dep_match = re.match(r"^([a-zA-Z0-9_\-\.]+)([<>=~\^]+)(.+)$", line)
                if dep_match:
                    name = dep_match.group(1)
                    constraint_type = dep_match.group(2)
                    version = dep_match.group(3)

                    dependencies.append(
                        {
                            "name": name,
                            "version": version,
                            "constraints": f"{constraint_type}{version}",
                            "is_dev": False,  # requirements.txt doesn't differentiate
                        }
                    )
                else:
                    # Simple case like 'package' with no version
                    if re.match(r"^[a-zA-Z0-9_\-\.]+$", line):
                        dependencies.append(
                            {
                                "name": line,
                                "version": "latest",
                                "constraints": "Not specified",
                                "is_dev": False,
                            }
                        )

        return {
            "dependency_count": len(dependencies),
            "dependencies": dependencies,
            "dev_dependency_count": 0,
            "dev_dependencies": [],
        }

    def _calculate_dependency_stats(self, dependencies: List[Dict]) -> Dict:
        """
        Calculate statistics about dependencies

        Args:
            dependencies: List of dependency dictionaries

        Returns:
            Dictionary with dependency statistics
        """
        stats = {
            "constraint_types": {},
            "exact_version_count": 0,
            "range_version_count": 0,
            "latest_count": 0,
        }

        for dep in dependencies:
            constraint = dep["constraints"]

            # Count constraint types
            if constraint == "Not specified" or constraint == "latest":
                stats["latest_count"] += 1
                constraint_type = "unconstrained"
            elif "==" in constraint:
                stats["exact_version_count"] += 1
                constraint_type = "exact"
            else:
                stats["range_version_count"] += 1

                if ">=" in constraint:
                    constraint_type = "minimum"
                elif "~=" in constraint:
                    constraint_type = "compatible"
                elif "^" in constraint:
                    constraint_type = "caret"
                else:
                    constraint_type = "other"

            # Update constraint type counts
            stats["constraint_types"][constraint_type] = (
                stats["constraint_types"].get(constraint_type, 0) + 1
            )

        return stats

    def build_dependency_tree(self) -> Dict:
        """
        Build a tree of dependencies and their relationships

        Returns:
            Dictionary with dependency tree information
        """
        if not self.has_poetry:
            return {
                "error": "Poetry not found, dependency tree only supported with Poetry"
            }

        logger.info("Building dependency tree using Poetry")

        try:
            # Run poetry show --tree to get dependency tree
            process = subprocess.run(
                ["poetry", "show", "--tree"],
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )

            if process.returncode != 0:
                logger.error(f"Error running 'poetry show --tree': {process.stderr}")
                return {"error": f"Failed to get dependency tree: {process.stderr}"}

            # Parse the tree output
            output = process.stdout
            tree = self._parse_poetry_tree(output)

            # Store for later use
            self.dependency_tree = tree

            return {
                "dependency_tree": tree,
                "dependency_count": len(tree),
                "max_depth": self._calculate_tree_depth(tree),
            }

        except FileNotFoundError:
            return {
                "error": "Poetry command not found. Please install Poetry or add it to your PATH."
            }
        except Exception as e:
            logger.error(f"Error building dependency tree: {e}")
            return {"error": str(e)}

    def _parse_poetry_tree(self, tree_output: str) -> Dict:
        """
        Parse dependency tree from poetry show --tree output

        Args:
            tree_output: Output from poetry show --tree command

        Returns:
            Dictionary representation of dependency tree
        """
        tree = {}
        current_top_level = None
        current_indent = 0

        for line in tree_output.split("\n"):
            if not line.strip():
                continue

            # Calculate indent level
            indent = len(line) - len(line.lstrip())
            clean_line = line.strip()

            # Extract name and version
            name_version_match = re.match(
                r"^([a-zA-Z0-9_\-\.]+) ([^!]+).*$", clean_line
            )
            if not name_version_match:
                continue

            name = name_version_match.group(1)
            version = name_version_match.group(2).strip()

            # Handle top-level dependencies
            if indent == 0:
                current_top_level = name
                current_indent = 0

                if name not in tree:
                    tree[name] = {
                        "name": name,
                        "version": version,
                        "dependencies": [],
                        "required_by": [],
                    }
            else:
                # This is a sub-dependency
                if current_top_level:
                    # Make sure the parent exists
                    if current_top_level not in tree:
                        tree[current_top_level] = {
                            "name": current_top_level,
                            "version": "unknown",
                            "dependencies": [],
                            "required_by": [],
                        }

                    # Add dependency to the tree
                    if name not in tree:
                        tree[name] = {
                            "name": name,
                            "version": version,
                            "dependencies": [],
                            "required_by": [current_top_level],
                        }
                    else:
                        if current_top_level not in tree[name]["required_by"]:
                            tree[name]["required_by"].append(current_top_level)

                    # Add to parent's dependencies
                    if name not in tree[current_top_level]["dependencies"]:
                        tree[current_top_level]["dependencies"].append(name)

        return tree

    def _calculate_tree_depth(self, tree: Dict) -> int:
        """
        Calculate the maximum depth of a dependency tree

        Args:
            tree: Dictionary representation of dependency tree

        Returns:
            Maximum depth of the tree
        """
        visited = set()

        def get_depth(name, depth=0):
            if name in visited:
                return depth

            visited.add(name)

            if name not in tree:
                return depth

            if not tree[name]["dependencies"]:
                return depth

            return max(get_depth(dep, depth + 1) for dep in tree[name]["dependencies"])

        depths = [get_depth(name) for name in tree.keys()]
        return max(depths) + 1 if depths else 0

    def analyze_lockfile(self) -> Dict:
        """
        Analyze the poetry.lock file

        Returns:
            Dictionary with lockfile analysis results
        """
        if not self.has_poetry:
            return {
                "error": "Poetry not found, lockfile analysis only supported with Poetry"
            }

        lockfile_path = self.project_root / "poetry.lock"

        if not lockfile_path.exists():
            return {"error": "poetry.lock not found"}

        logger.info(f"Analyzing lockfile at {lockfile_path}")

        # Get file stats
        file_size = lockfile_path.stat().st_size

        # Count entries in lockfile
        package_count = 0
        with open(lockfile_path, "r") as f:
            content = f.read()
            # Count package sections
            package_count = content.count("\n[[package]]")

        # Get lockfile metadata
        metadata = {}
        metadata_match = re.search(r"\[metadata\](.*?)(\[|\Z)", content, re.DOTALL)
        if metadata_match:
            metadata_str = metadata_match.group(1)

            # Extract metadata fields
            for field in ["lock-version", "python-versions", "content-hash"]:
                field_match = re.search(f'{field} = "([^"]+)"', metadata_str)
                if field_match:
                    metadata[field] = field_match.group(1)

        return {
            "lockfile_exists": True,
            "file_size_bytes": file_size,
            "package_count": package_count,
            "metadata": metadata,
        }

    def compare_with_requirements(self) -> Dict:
        """
        Compare Poetry dependencies with requirements.txt

        Returns:
            Dictionary with comparison results
        """
        if not self.has_poetry or not self.has_requirements:
            return {
                "error": "Both Poetry and requirements.txt are needed for comparison"
            }

        # Analyze both dependency sources
        poetry_deps = self._analyze_poetry_dependencies()
        req_deps = self._analyze_requirements_txt()

        # Convert to dictionaries for easier comparison
        poetry_dep_dict = {d["name"].lower(): d for d in poetry_deps["dependencies"]}
        req_dep_dict = {d["name"].lower(): d for d in req_deps["dependencies"]}

        # Find common, unique, and conflicting dependencies
        common = []
        only_in_poetry = []
        only_in_requirements = []
        conflicts = []

        for name, dep in poetry_dep_dict.items():
            if name in req_dep_dict:
                # Found in both
                req_dep = req_dep_dict[name]

                # Check if versions conflict
                poetry_constraint = dep["constraints"]
                req_constraint = req_dep["constraints"]

                common.append(
                    {
                        "name": name,
                        "poetry_version": poetry_constraint,
                        "requirements_version": req_constraint,
                    }
                )

                # Simple check for obvious conflicts (exact versions that don't match)
                if (
                    "==" in poetry_constraint
                    and "==" in req_constraint
                    and poetry_constraint != req_constraint
                ):
                    conflicts.append(
                        {
                            "name": name,
                            "poetry_version": poetry_constraint,
                            "requirements_version": req_constraint,
                        }
                    )
            else:
                # Only in poetry
                only_in_poetry.append(
                    {
                        "name": name,
                        "version": dep["version"],
                        "constraints": dep["constraints"],
                    }
                )

        # Find dependencies only in requirements.txt
        for name, dep in req_dep_dict.items():
            if name not in poetry_dep_dict:
                only_in_requirements.append(
                    {
                        "name": name,
                        "version": dep["version"],
                        "constraints": dep["constraints"],
                    }
                )

        return {
            "common_dependencies": common,
            "only_in_poetry": only_in_poetry,
            "only_in_requirements": only_in_requirements,
            "conflicting_versions": conflicts,
            "common_count": len(common),
            "only_in_poetry_count": len(only_in_poetry),
            "only_in_requirements_count": len(only_in_requirements),
            "conflicts_count": len(conflicts),
        }

    def generate_report(self) -> Dict:
        """
        Generate a comprehensive dependency management report

        Returns:
            Dictionary with the full analysis report
        """
        logger.info("Generating dependency management report")

        # Analyze dependencies
        dep_analysis = self.analyze_dependencies()

        # Add lockfile analysis if available
        lockfile_analysis = {}
        if self.has_poetry:
            lockfile_analysis = self.analyze_lockfile()

        # Build dependency tree if poetry is available
        tree_analysis = {}
        if self.has_poetry:
            tree_analysis = self.build_dependency_tree()

        # Compare with requirements.txt if both are available
        comparison = {}
        if self.has_poetry and self.has_requirements:
            comparison = self.compare_with_requirements()

        # Generate recommendations
        recommendations = self._generate_recommendations(
            dep_analysis, lockfile_analysis, tree_analysis, comparison
        )

        # Compile the report
        report = {
            "project_root": str(self.project_root),
            "dependency_analysis": dep_analysis,
            "lockfile_analysis": lockfile_analysis,
            "dependency_tree": tree_analysis,
            "requirements_comparison": comparison,
            "recommendations": recommendations,
        }

        return report

    def _generate_recommendations(
        self,
        dep_analysis: Dict,
        lockfile_analysis: Dict,
        tree_analysis: Dict,
        comparison: Dict,
    ) -> List[str]:
        """
        Generate recommendations based on the analysis

        Args:
            dep_analysis: Dependency analysis results
            lockfile_analysis: Lockfile analysis results
            tree_analysis: Dependency tree analysis results
            comparison: Requirements.txt comparison results

        Returns:
            List of recommendations
        """
        recommendations = []

        # Check if using both Poetry and requirements.txt
        if self.has_poetry and self.has_requirements:
            if comparison.get("conflicts_count", 0) > 0:
                recommendations.append(
                    "CRITICAL: Found conflicting versions between Poetry and requirements.txt. "
                    "This can lead to inconsistent environments. Choose one tool as the source of truth."
                )

            recommendations.append(
                "Consider using either Poetry or requirements.txt as the single source of truth "
                "for dependencies, not both. This simplifies dependency management."
            )

            # If requirements.txt has unique dependencies, suggest adding them to Poetry
            if comparison.get("only_in_requirements_count", 0) > 0:
                recommendations.append(
                    f"Found {comparison.get('only_in_requirements_count')} dependencies only in requirements.txt. "
                    "Consider adding them to pyproject.toml for complete dependency management with Poetry."
                )

        # Check version constraints
        stats = dep_analysis.get("dependency_stats", {})
        latest_count = stats.get("latest_count", 0)

        if latest_count > 0 and dep_analysis.get("dependency_count", 0) > 0:
            latest_pct = (latest_count / dep_analysis["dependency_count"]) * 100
            if latest_pct > 20:
                recommendations.append(
                    f"{latest_count} dependencies ({latest_pct:.1f}%) don't specify version constraints. "
                    "Consider adding version constraints to improve reproducibility."
                )

        # Check lockfile
        if self.has_poetry and lockfile_analysis.get("lockfile_exists", False):
            lock_packages = lockfile_analysis.get("package_count", 0)
            direct_deps = dep_analysis.get("dependency_count", 0) + dep_analysis.get(
                "dev_dependency_count", 0
            )

            if lock_packages > 0 and direct_deps > 0:
                ratio = lock_packages / direct_deps
                if ratio > 5:
                    recommendations.append(
                        f"Your dependency tree is quite deep (direct:transitive ratio is 1:{ratio:.1f}). "
                        "Consider reviewing indirect dependencies for potential simplification."
                    )

        # Check for dependency conflicts in tree
        if tree_analysis and "dependency_tree" in tree_analysis:
            tree = tree_analysis.get("dependency_tree", {})
            multi_required = [
                name
                for name, info in tree.items()
                if len(info.get("required_by", [])) > 1
            ]

            if len(multi_required) > 3:
                recommendations.append(
                    f"Found {len(multi_required)} dependencies required by multiple packages. "
                    "This increases the risk of version conflicts. Consider simplifying the dependency tree."
                )

        # General recommendations
        if self.has_poetry:
            recommendations.append(
                "Use Poetry's groups feature to organize dependencies by purpose "
                "(e.g., dev, test, docs) for better dependency management."
            )

            recommendations.append(
                "Regularly update dependencies with 'poetry update' and review the changes "
                "to stay current with security fixes while maintaining stability."
            )
        else:
            recommendations.append(
                "Consider adopting Poetry for dependency management. It provides better "
                "dependency resolution, environment management, and package publishing capabilities."
            )

        return recommendations


def run_install_test(project_path: str, temp_dir: str = None) -> Dict:
    """
    Test dependency installation methods for speed and reliability

    Args:
        project_path: Path to project to test
        temp_dir: Directory to use for temporary virtual environments

    Returns:
        Dictionary with test results
    """
    project_path = Path(project_path)

    # Create a temporary directory if none provided
    if temp_dir is None:
        temp_dir = tempfile.mkdtemp()
    else:
        temp_dir = Path(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)

    logger.info(f"Running installation tests in {temp_dir}")

    results = {"pip_install": {}, "poetry_install": {}}

    # Test pip install with requirements.txt
    req_path = project_path / "requirements.txt"
    if req_path.exists():
        pip_venv = temp_dir / "pip_venv"
        logger.info(f"Creating pip virtual environment at {pip_venv}")

        try:
            # Create virtual environment
            subprocess.run([sys.executable, "-m", "venv", str(pip_venv)], check=True)

            # Determine pip command
            if os.name == "nt":  # Windows
                pip_cmd = str(pip_venv / "Scripts" / "pip")
            else:  # Unix/Mac
                pip_cmd = str(pip_venv / "bin" / "pip")

            # Install dependencies
            start_time = time.time()
            process = subprocess.run(
                [pip_cmd, "install", "-r", str(req_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            install_time = time.time() - start_time

            if process.returncode == 0:
                # Count installed packages
                process = subprocess.run(
                    [pip_cmd, "list", "--format=json"],
                    stdout=subprocess.PIPE,
                    universal_newlines=True,
                )

                try:
                    packages = json.loads(process.stdout)
                    package_count = len(packages)
                except json.JSONDecodeError:
                    package_count = 0

                results["pip_install"] = {
                    "success": True,
                    "install_time_seconds": install_time,
                    "package_count": package_count,
                }
            else:
                results["pip_install"] = {
                    "success": False,
                    "error": process.stderr,
                    "install_time_seconds": install_time,
                }
        except Exception as e:
            logger.error(f"Error with pip installation test: {e}")
            results["pip_install"] = {"success": False, "error": str(e)}
    else:
        results["pip_install"] = {
            "success": False,
            "error": "requirements.txt not found",
        }

    # Test poetry install
    if (project_path / "pyproject.toml").exists():
        poetry_dir = temp_dir / "poetry_project"
        os.makedirs(poetry_dir, exist_ok=True)

        try:
            # Copy pyproject.toml and poetry.lock if it exists
            shutil.copy(project_path / "pyproject.toml", poetry_dir / "pyproject.toml")

            lockfile = project_path / "poetry.lock"
            if lockfile.exists():
                shutil.copy(lockfile, poetry_dir / "poetry.lock")

            # Run poetry install
            start_time = time.time()
            process = subprocess.run(
                ["poetry", "install"],
                cwd=str(poetry_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            install_time = time.time() - start_time

            if process.returncode == 0:
                # Get package count from poetry show
                process = subprocess.run(
                    ["poetry", "show", "--no-dev"],
                    cwd=str(poetry_dir),
                    stdout=subprocess.PIPE,
                    universal_newlines=True,
                )

                package_count = len(process.stdout.strip().split("\n"))

                results["poetry_install"] = {
                    "success": True,
                    "install_time_seconds": install_time,
                    "package_count": package_count,
                }
            else:
                results["poetry_install"] = {
                    "success": False,
                    "error": process.stderr,
                    "install_time_seconds": install_time,
                }
        except Exception as e:
            logger.error(f"Error with poetry installation test: {e}")
            results["poetry_install"] = {"success": False, "error": str(e)}
    else:
        results["poetry_install"] = {
            "success": False,
            "error": "pyproject.toml not found",
        }

    return results


def main():
    """Run dependency management tests and generate report"""
    logger.info("Starting Dependency Management Tests")

    # Find project root
    project_root = Path(__file__).parent.parent.parent

    print("\nDependency Management Analysis")
    print("=============================\n")

    print(f"Analyzing project at: {project_root}")

    # Perform dependency analysis
    analyzer = DependencyAnalyzer(project_root)
    report = analyzer.generate_report()

    # Print report summary
    has_poetry = report["dependency_analysis"]["poetry_found"]
    has_requirements = report["dependency_analysis"]["requirements_found"]

    print("\nDependency Management Tools:")
    print(f"  Using Poetry: {'Yes' if has_poetry else 'No'}")
    print(f"  Using requirements.txt: {'Yes' if has_requirements else 'No'}")

    if has_poetry:
        dep_count = report["dependency_analysis"]["dependency_count"]
        dev_count = report["dependency_analysis"]["dev_dependency_count"]
        print(f"\nPoetry Dependencies: {dep_count} main, {dev_count} dev dependencies")

        if (
            "lockfile_analysis" in report
            and "package_count" in report["lockfile_analysis"]
        ):
            lock_count = report["lockfile_analysis"]["package_count"]
            print(f"Total dependencies (including transitive): {lock_count}")

    if has_requirements:
        req_count = report["dependency_analysis"]["dependency_count"]
        print(f"\nrequirements.txt Dependencies: {req_count} dependencies")

    print("\nRecommendations:")
    for i, rec in enumerate(report["recommendations"], 1):
        print(f"  {i}. {rec}")

    # Option to run installation tests
    should_test = (
        input("\nRun installation tests for comparison? (y/n): ").strip().lower() == "y"
    )

    if should_test:
        print("\nRunning installation tests (this may take a few minutes)...")
        test_results = run_install_test(project_root)

        print("\nInstallation Test Results:")

        if "pip_install" in test_results and test_results["pip_install"].get(
            "success", False
        ):
            pip_time = test_results["pip_install"]["install_time_seconds"]
            pip_count = test_results["pip_install"]["package_count"]
            print(
                f"  pip install -r requirements.txt: {pip_time:.2f}s, {pip_count} packages"
            )
        elif "pip_install" in test_results:
            print(
                f"  pip install failed: {test_results['pip_install'].get('error', 'Unknown error')}"
            )

        if "poetry_install" in test_results and test_results["poetry_install"].get(
            "success", False
        ):
            poetry_time = test_results["poetry_install"]["install_time_seconds"]
            poetry_count = test_results["poetry_install"]["package_count"]
            print(f"  poetry install: {poetry_time:.2f}s, {poetry_count} packages")
        elif "poetry_install" in test_results:
            print(
                f"  poetry install failed: {test_results['poetry_install'].get('error', 'Unknown error')}"
            )

        # Compare times if both succeeded
        if test_results["pip_install"].get("success", False) and test_results[
            "poetry_install"
        ].get("success", False):

            pip_time = test_results["pip_install"]["install_time_seconds"]
            poetry_time = test_results["poetry_install"]["install_time_seconds"]

            if pip_time < poetry_time:
                diff_pct = ((poetry_time / pip_time) - 1) * 100
                print(f"\nPip is faster by {diff_pct:.1f}%")
            else:
                diff_pct = ((pip_time / poetry_time) - 1) * 100
                print(f"\nPoetry is faster by {diff_pct:.1f}%")

            # Add installation results to the report
            report["installation_tests"] = test_results

    # Save report to file
    report_path = (
        project_root
        / "research"
        / "devops_practices"
        / "dependency_management_report.json"
    )
    os.makedirs(report_path.parent, exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nDetailed report saved to: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
