"""
Research validation runner for HORAO research components.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

RESEARCH_DIR = Path(__file__).parent.parent / "research"


def run_validation_script(script_path):
    """Run a validation script and return its exit code."""
    logger.info(f"Running validation: {script_path}")
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True,
        text=True,
        check=False,
    )

    # Log output
    if result.stdout:
        for line in result.stdout.splitlines():
            logger.info(f"[{script_path.parent.name}] {line}")

    if result.stderr:
        for line in result.stderr.splitlines():
            if "error" in line.lower() or "exception" in line.lower():
                logger.error(f"[{script_path.parent.name}] {line}")
            else:
                logger.warning(f"[{script_path.parent.name}] {line}")

    return result.returncode


def run_all_validations():
    """Find and run all validation scripts in the research directory."""
    logger.info("Starting HORAO research validation suite")

    validation_scripts = []
    failed_validations = []

    # Find all run_validation.py scripts
    for dirpath, _, filenames in os.walk(RESEARCH_DIR):
        for filename in filenames:
            if filename == "run_validation.py":
                validation_scripts.append(Path(dirpath) / filename)

    if not validation_scripts:
        logger.error("No validation scripts found in research directory")
        return 1

    logger.info(f"Found {len(validation_scripts)} validation scripts")

    # Run each validation script
    for script_path in sorted(validation_scripts):
        research_area = script_path.parent.name
        logger.info(f"Running validation for research area: {research_area}")

        exit_code = run_validation_script(script_path)

        if exit_code != 0:
            logger.error(
                f"Validation failed for {research_area} with exit code {exit_code}"
            )
            failed_validations.append(research_area)
        else:
            logger.info(f"Validation completed successfully for {research_area}")

    # Report results
    total = len(validation_scripts)
    failed = len(failed_validations)
    success = total - failed

    logger.info("=" * 60)
    logger.info(f"HORAO Research Validation Summary:")
    logger.info(f"Total: {total} | Succeeded: {success} | Failed: {failed}")

    if failed:
        logger.error(f"Failed research areas: {', '.join(failed_validations)}")
        return 1
    else:
        logger.info("All research validations completed successfully")
        return 0


if __name__ == "__main__":
    sys.exit(run_all_validations())
