#!/usr/bin/env python3
"""
Test canonical solutions against their test cases.

This script validates quantum computing solutions in the Qiskit Human Eval dataset by
executing canonical solutions with their test cases in isolated, secure environments.

Security Features:
    - Execution timeout (30s) to prevent infinite loops
    - Isolated namespace for safe code execution
    - Version-controlled dataset with code review requirements

Key Features:
    - Test all datasets or filter by specific dataset/task
    - Verbose logging for detailed debugging
    - JSON output for CI/CD integration
    - Comprehensive error reporting with configurable detail levels

Usage Examples:
    Test all datasets:
        $ python scripts/test_solutions.py

    Test specific dataset:
        $ python scripts/test_solutions.py -d dataset/dataset_qiskit_test_human_eval.json

    Test specific task across all datasets:
        $ python scripts/test_solutions.py -t qiskitHumanEval/42

    Exclude 'prompt' field value from execution:
        $ python scripts/test_solutions.py -e -t qiskitHumanEval/42

    Enable detailed logging:
        $ python scripts/test_solutions.py -v

    Output results to JSON file:
        $ python scripts/test_solutions.py -o results.json

    Combine multiple options:
        $ python scripts/test_solutions.py -v -d dataset/custom.json -o results.json

Exit Codes:
    0: All tests passed successfully
    1: One or more tests failed or an error occurred

Output:
    - Console: Human-readable test results with pass/fail indicators
    - JSON (optional): Machine-readable structured results

For more information, see: scripts/README.md

Security Warning:
    This script uses exec() to execute code from the dataset. Only run this on
    trusted, version-controlled datasets.
"""

import argparse
import json
import logging
import signal
import sys
import time
import traceback
from contextlib import contextmanager
from pathlib import Path
from typing import Any


# Configure module logger
logger = logging.getLogger(__name__)

# Configuration constants
MAX_FAILURES_TO_SHOW = 15
MAX_ERROR_LINES_TO_SHOW = 10

# Execution timeout (in seconds) to prevent infinite loops
EXECUTION_TIMEOUT_SECONDS = 30

# Default datasets to test when no specific dataset is provided
# List of tuple indicating path to dataset and boolean (True if 'prompt' field should be excluded from execution)
DEFAULT_DATASETS = [
    (Path("dataset/dataset_qiskit_test_human_eval.json"), False),
    (Path("dataset/dataset_qiskit_test_human_eval_hard.json"), True),
]


@contextmanager
def timeout(seconds: int):
    """
    Context manager to enforce a timeout on code execution.

    Uses SIGALRM signal to interrupt execution after the specified time limit.
    This prevents infinite loops and resource exhaustion attacks.

    Args:
        seconds (int): Maximum number of seconds to allow execution

    Raises:
        TimeoutError: If execution exceeds the specified timeout

    Example:
        Use as a context manager to limit execution time:
        with timeout(5):
            result = expensive_computation()

    Note:
        Only works on Unix-like systems (uses signal.SIGALRM).
        Not available on Windows.
    """

    def timeout_handler(signum, frame):
        raise TimeoutError(f"Execution exceeded {seconds} seconds")

    # Set the signal handler and alarm
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        # Restore the old handler and cancel the alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def test_problem(
    problem: dict[str, Any], exclude_prompt: bool = False
) -> tuple[bool, str | None, str | None]:
    """
    Test a single problem's canonical solution against its test case.

    Executes the problem's canonical solution in a restricted, isolated namespace
    with timeout protection. Combines the prompt (optional), solution, and test code,
    then runs the test's check function against the implemented entry point.

    Args:
        problem (dict[str, Any]): Problem dictionary containing:
            - task_id (str): Unique identifier for the problem
            - prompt (str): Problem description and function signature
            - canonical_solution (str): Reference implementation
            - test (str): Test code with check function
            - entry_point (str): Name of the function to test
        exclude_prompt (bool, optional): If True, don't prepend prompt to execution.
                                        Defaults to False.

    Returns:
        tuple[bool, Optional[str]]: A tuple containing:
            - success (bool): True if test passed, False otherwise
            - error_message (str | None): Error description if failed, None if passed
    """
    task_id = problem.get("task_id", "unknown")
    logger.debug(f"Testing problem: {task_id}")
    code: str = ""

    try:
        # Create executable code by combining prompt, solution, and test
        prompt = "" if exclude_prompt else problem["prompt"]
        code = prompt + "\n" + problem["canonical_solution"] + "\n" + problem["test"]

        logger.debug(f"Code length for {task_id}: {len(code)} characters")
        if exclude_prompt:
            logger.debug(f"Prompt excluded for {task_id}")

        # ⚠️  SECURITY WARNING: exec() Execution
        # This script uses exec() to execute code from the dataset.
        # ONLY run this script on code you trust from version-controlled sources.
        # exec() can execute arbitrary code and is dangerous if used with untrusted input.
        #
        # For this project, this is safe because:
        # - Dataset is version-controlled in Git
        # - All changes require code review
        # - Only runs on trusted developer/CI systems
        #
        # DO NOT use this script with:
        # - User-submitted code
        # - Untrusted data sources
        # - Network-provided solutions
        #
        # See: security-analysis-exec.md for detailed security analysis

        # Execute the code in a restricted namespace with timeout protection
        namespace: dict[str, Any] = {}

        logger.debug(f"Executing code for {task_id} with {EXECUTION_TIMEOUT_SECONDS}s timeout")
        with timeout(EXECUTION_TIMEOUT_SECONDS):
            exec(code, namespace)

        # Run the check function against the implemented function
        entry_point = problem["entry_point"]
        logger.debug(f"Checking entry point: {entry_point}")

        if entry_point not in namespace:
            logger.warning(f'Entry point "{entry_point}" not found in namespace for {task_id}')
            return False, f'Entry point "{entry_point}" not defined', code

        namespace["check"](namespace[entry_point])
        logger.info(f"✓ {task_id} passed")
        return True, None, code

    except TimeoutError as e:
        logger.error(f"✗ {task_id} timed out: {e}")
        return False, f"Execution timeout: {e}", code
    except AssertionError as e:
        logger.error(f"✗ {task_id} assertion failed: {e}")
        return False, f"Test assertion failed: {e}", code
    except Exception as e:
        # Include full traceback for debugging
        error_detail = traceback.format_exc()
        logger.error(f"✗ {task_id} failed with {type(e).__name__}: {e}")
        logger.debug(f"Full traceback for {task_id}:\n{error_detail}")
        return False, f"{type(e).__name__}: {e}\n{error_detail}", code


def test_dataset(
    filepath: Path, task_id_filter: str | None = None, exclude_prompt: bool = False
) -> tuple[int, list[dict[str, str]]]:
    """
    Test all canonical solutions in a dataset.

    Loads a JSON dataset file and tests each problem's canonical solution.
    Can optionally filter to test only a specific task_id.

    Args:
        filepath (Path): Path to dataset JSON file containing list of problems
        task_id_filter (Optional[str], optional): If provided, only test the problem
                                                  with this task_id. If None, tests
                                                  all problems. Defaults to None.
        exclude_prompt (bool, optional): If True, don't prepend prompt to execution.
                                        Defaults to False.

    Returns:
        tuple[int, list[dict[str, str]]]: A tuple containing:
            - passed_count (int): Number of problems that passed
            - failures (list[dict]): List of failure dicts, each with:
                - 'task_id' (str): The failing task identifier
                - 'error' (str): Detailed error message
    """
    logger.info(f"Loading dataset: {filepath}")

    try:
        with filepath.open() as f:
            data = json.load(f)
        logger.debug(f"Loaded {len(data)} problems from {filepath}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        return 0, [{"task_id": "N/A", "error": f"Invalid JSON: {e}"}]
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        return 0, [{"task_id": "N/A", "error": f"File not found: {filepath}"}]

    passed = 0
    failures = []
    found = False

    for idx, problem in enumerate(data):
        task_id = problem.get("task_id", f"unknown_{idx}")

        # If filtering by task_id, skip non-matching problems
        if task_id_filter is not None:
            if task_id != task_id_filter:
                continue
            found = True
            logger.debug(f"Found target task: {task_id}")

        # Validate problem structure first
        required_fields = {"task_id", "prompt", "canonical_solution", "test", "entry_point"}
        missing = required_fields - set(problem.keys())
        if missing:
            logger.warning(f"Problem {task_id} missing fields: {missing}")
            failures.append(
                {"task_id": task_id, "error": f"Missing required fields: {missing}", "code": "N/A"}
            )
            continue

        # Test the solution
        success, error, code = test_problem(problem, exclude_prompt)

        if success:
            passed += 1
        else:
            failures.append(
                {
                    "task_id": task_id,
                    "error": error,
                    "code": code,
                }
            )

    # If filtering by task_id and not found, return error
    if task_id_filter is not None and not found:
        logger.warning(f"Task {task_id_filter} not found in {filepath}")
        return 0, [{"task_id": task_id_filter, "error": f"Task not found in {filepath}"}]

    logger.info(f"Dataset {filepath}: {passed} passed, {len(failures)} failed")
    return passed, failures


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments using argparse.

    Defines and parses all CLI arguments for the test script including
    dataset filtering, task filtering, output options, and logging control.

    Returns:
        argparse.Namespace: Parsed arguments with attributes:
            - dataset (str | None): Path to specific dataset file
            - task (str | None): Specific task_id to test
            - exclude (bool): Whether to exclude prompt from execution
            - verbose (bool): Enable verbose logging
            - output (str | None): Path to JSON output file
    """
    parser = argparse.ArgumentParser(
        prog="test_solutions.py",
        description="Test canonical solutions against their test cases.",
        epilog="Examples:\n"
        "  python scripts/test_solutions.py\n"
        "  python scripts/test_solutions.py -d dataset/dataset_qiskit_test_human_eval.json\n"
        "  python scripts/test_solutions.py -t qiskitHumanEval/42 -o stdout\n"
        "  python scripts/test_solutions.py -d dataset/dataset_qiskit_test_human_eval.json -t qiskitHumanEval/42",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-d",
        "--dataset",
        metavar="<dataset file path>",
        dest="dataset",
        default=None,
        help="Test problems in a specific dataset",
    )

    parser.add_argument(
        "-t",
        "--task",
        metavar="<problem task id>",
        dest="task",
        default=None,
        help="Test a specific problem (searches all datasets if not combined with -d)",
    )

    parser.add_argument(
        "-e",
        "--exclude-prompt",
        dest="exclude",
        action="store_true",
        help="Do not prepend the prompt to the execution code (only applicable when dataset is provided)",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output with detailed logging"
    )

    parser.add_argument(
        "-o",
        "--output",
        metavar="<output file>",
        dest="output",
        default=None,
        help='Write test results to JSON file (use "stdout" or "-" to pipe to stdout)',
    )

    return parser.parse_args()


def write_json_output(
    output_path: Path | None,
    total_passed: int,
    total_tested: int,
    total_failures: list[tuple[Path, dict[str, str]]],
    dataset_results: dict[Path, dict[str, Any]],
    dataset_filter: Path | None,
    task_id_filter: str | None,
    exclude_prompt: bool,
    execution_time: float,
    to_stdout: bool = False,
) -> None:
    """
    Write test results to a JSON file or stdout.

    Creates a structured JSON output containing summary statistics, applied filters,
    per-dataset results, and detailed failure information.

    Args:
        output_path (Optional[Path]): Path where JSON file should be written (None if stdout)
        total_passed (int): Total number of tests that passed
        total_tested (int): Total number of tests executed
        total_failures (list[tuple[Path, dict]]): List of (dataset, failure) tuples
        dataset_results (dict[Path, dict]): Per-dataset test results
        dataset_filter (Optional[Path]): Dataset filter that was applied, if any
        task_id_filter (Optional[str]): Task ID filter that was applied, if any
        exclude_prompt (bool): Whether prompt was excluded from execution
        execution_time (float): Total execution time in seconds
        to_stdout (bool, optional): If True, write to stdout instead of file. Defaults to False.

    Raises:
        Exception: If file writing fails (logged but doesn't stop execution)
    """
    if not to_stdout:
        logger.info(f"Writing results to JSON file: {output_path}")

    try:
        # Prepare results data
        results = {
            "summary": {
                "total_passed": total_passed,
                "total_tested": total_tested,
                "total_failed": len(total_failures),
                "success": len(total_failures) == 0,
                "execution_time_seconds": round(execution_time, 2),
            },
            "filters": {
                "dataset": str(dataset_filter) if dataset_filter else None,
                "task_id": task_id_filter,
                "exclude_prompt": exclude_prompt,
            },
            "datasets": {
                str(dataset): {
                    "passed": result["passed"],
                    "total": result["total"],
                    "failed": len(result["failures"]),
                }
                for dataset, result in dataset_results.items()
            },
            "failures": [
                {
                    "task_id": failure["task_id"],
                    "dataset": str(dataset),
                    "error": failure["error"],
                    "code": failure.get("code", "N/A"),
                }
                for dataset, failure in total_failures
            ],
        }

        # Write to stdout or file
        if to_stdout:
            json.dump(results, sys.stdout, indent=2)
            sys.stdout.write("\n")  # Add newline for better formatting
            sys.stdout.flush()
        elif output_path:
            with output_path.open("w") as f:
                json.dump(results, f, indent=2)
            logger.info(f"Successfully wrote results to {output_path}")

    except Exception as e:
        if not to_stdout:
            logger.error(f"Failed to write JSON output: {e}")
        else:
            # Write error to stderr to not corrupt stdout JSON
            print(f"Error writing JSON: {e}", file=sys.stderr)


def print_test_summary(
    total_passed: int,
    total_tested: int,
    total_failures: list[tuple[Path, dict[str, str]]],
    task_id_filter: str | None,
    dataset_filter: Path | None,
    task_found_count: int,
    max_failures_to_show: int,
    max_error_lines_to_show: int,
) -> int:
    """
    Print test summary and failure details to console.

    Displays summary statistics and detailed failure information based on the
    test results. Returns appropriate exit code.

    Args:
        total_passed (int): Total number of tests that passed
        total_tested (int): Total number of tests executed
        total_failures (list[tuple[Path, dict]]): List of (dataset, failure) tuples
        task_id_filter (Optional[str]): Task ID filter that was applied, if any
        dataset_filter (Optional[Path]): Dataset filter that was applied, if any
        task_found_count (int): Number of datasets where task was found (for task filtering)
        max_failures_to_show (int): Maximum number of failures to display
        max_error_lines_to_show (int): Maximum number of error lines per failure

    Returns:
        int: Exit code - 0 for success, 1 for failure
    """
    # Print summary based on filter type
    if task_id_filter:
        if task_found_count > 0:
            logger.info(f"Result: {total_passed} passed in {task_found_count} dataset(s)")
        else:
            logger.info(f"Result: Task {task_id_filter} not found in any dataset")
    elif dataset_filter:
        logger.info(f"Results: {total_passed}/{total_tested} passed in {dataset_filter}")
    else:
        logger.info(f"Results: {total_passed}/{total_tested} passed")

    # Print failure details if any
    if total_failures:
        logger.info(f"Testing failed with {len(total_failures)} failure(s)")

        for dataset, failure in total_failures[:max_failures_to_show]:
            print(f"    {failure['task_id']} in {dataset}:")
            error_lines = failure["error"].split("\n")
            # Show first N lines of error, then truncate if too long
            for line in error_lines[:max_error_lines_to_show]:
                print(f"      {line}")
            if len(error_lines) > max_error_lines_to_show:
                print(
                    f"      ... (truncated, {len(error_lines) - max_error_lines_to_show} more lines)"
                )

        if len(total_failures) > max_failures_to_show:
            print(f"    ... and {len(total_failures) - max_failures_to_show} more failures")

        return 1
    else:
        if task_id_filter:
            logger.info(f"Task {task_id_filter} passed in all datasets")
        elif dataset_filter:
            logger.info(f"All {total_passed} canonical solutions in {dataset_filter} passed")
        else:
            logger.info(f"All {total_passed} canonical solutions passed")
        return 0


def main(
    max_failures_to_show: int = MAX_FAILURES_TO_SHOW,
    max_error_lines_to_show: int = MAX_ERROR_LINES_TO_SHOW,
) -> int:
    """
    Run tests on datasets. Optionally filter by dataset file path and/or task_id.

    Args:
        max_failures_to_show: Maximum number of failures to display in output
        max_error_lines_to_show: Maximum number of error lines to show per failure

    Returns:
        Exit code: 0 for success, 1 for failure
    """
    # Parse command-line arguments
    args = parse_arguments()

    # Setup logging based on verbosity
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)-8s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Start timing
    start_time = time.time()

    # Check if output should go to stdout
    output_to_stdout = args.output and args.output.lower() in ["stdout", "-"]

    # Suppress console logging if outputting JSON to stdout
    if output_to_stdout:
        logging.disable(logging.CRITICAL)

    logger.info("Starting test_solutions.py")
    if args.verbose:
        logger.debug("Verbose mode enabled")

    # Extract arguments and convert to Path objects
    dataset_filter = Path(args.dataset) if args.dataset else None
    task_id_filter = args.task
    exclude_prompt = args.exclude

    logger.debug(
        f"Arguments: dataset={dataset_filter}, task={task_id_filter}, exclude_prompt={exclude_prompt}"
    )

    # Determine which datasets to test
    if dataset_filter:
        # Verify the dataset file exists
        logger.debug(f"Validating dataset file: {dataset_filter}")
        try:
            with dataset_filter.open() as f:
                json.load(f)
            datasets = [(dataset_filter, exclude_prompt)]
            logger.info(f"Using dataset: {dataset_filter}")
        except FileNotFoundError:
            logger.error(f"Dataset file not found: {dataset_filter}")
            return 1
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {dataset_filter}: {e}")
            return 1
    else:
        # If only task_id is specified (no dataset), search all datasets
        # If both task_id and dataset are specified, only search specified dataset
        datasets = DEFAULT_DATASETS
        logger.info(f"Using default datasets: {[str(d) for d, _ in datasets]}")

    total_passed = 0
    total_failures: list[tuple[Path, dict[str, str]]] = []
    dataset_results: dict[Path, dict[str, Any]] = {}
    task_found_count = 0

    # Print what we're testing
    if task_id_filter:
        logger.info(f"Testing task: {task_id_filter}")

    for dataset, exclude_prompts in datasets:
        if task_id_filter:
            logger.debug(f"Searching for task {task_id_filter} in {dataset}")
        else:
            logger.debug(f"Testing all problems in {dataset}")

        passed, failures = test_dataset(
            dataset, task_id_filter=task_id_filter, exclude_prompt=exclude_prompts
        )

        dataset_results[dataset] = {
            "passed": passed,
            "total": passed + len(failures),
            "failures": failures,
        }

        # Count how many datasets found the task
        if task_id_filter and passed > 0:
            task_found_count += 1

        total_passed += passed
        total_failures.extend([(dataset, f) for f in failures])

    # Calculate execution time
    execution_time = time.time() - start_time

    # Calculate total tested
    total_tested = sum(r["total"] for r in dataset_results.values())

    # Determine exit code
    exit_code = 1 if total_failures else 0

    # Handle output based on mode
    if output_to_stdout:
        # Output JSON to stdout (for piping)
        write_json_output(
            output_path=None,
            total_passed=total_passed,
            total_tested=total_tested,
            total_failures=total_failures,
            dataset_results=dataset_results,
            dataset_filter=dataset_filter,
            task_id_filter=task_id_filter,
            exclude_prompt=exclude_prompt,
            execution_time=execution_time,
            to_stdout=True,
        )
    else:
        # Normal mode: print summary and optionally write JSON to file
        logger.info(f"Total execution time: {execution_time:.2f} seconds")

        exit_code = print_test_summary(
            total_passed=total_passed,
            total_tested=total_tested,
            total_failures=total_failures,
            task_id_filter=task_id_filter,
            dataset_filter=dataset_filter,
            task_found_count=task_found_count,
            max_failures_to_show=max_failures_to_show,
            max_error_lines_to_show=max_error_lines_to_show,
        )

        # Write JSON output to file if requested
        if args.output:
            write_json_output(
                output_path=Path(args.output),
                total_passed=total_passed,
                total_tested=total_tested,
                total_failures=total_failures,
                dataset_results=dataset_results,
                dataset_filter=dataset_filter,
                task_id_filter=task_id_filter,
                exclude_prompt=exclude_prompt,
                execution_time=execution_time,
                to_stdout=False,
            )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
