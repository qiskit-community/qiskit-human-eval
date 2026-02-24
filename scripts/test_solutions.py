#!/usr/bin/env python3
"""Test canonical solutions against their test cases."""

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Optional, Tuple

# Global configuration for failure reporting
MAX_FAILURES_TO_SHOW = 15
MAX_ERROR_LINES_TO_SHOW = 10


def test_problem(problem: dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Test a single problem's canonical solution against its test case.

    Args:
        problem: Dictionary with keys: task_id, prompt, canonical_solution, test, entry_point

    Returns:
        Tuple of (success: bool, error_message: str or None)
    """
    task_id = problem.get('task_id', 'unknown')

    try:
        # Create executable code by combining prompt, solution, and test
        code = (
            problem['prompt'] + '\n' +
            problem['canonical_solution'] + '\n' +
            problem['test']
        )

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

        # Execute the code in a fresh namespace
        namespace = {}
        exec(code, namespace)

        # Run the check function against the implemented function
        entry_point = problem['entry_point']
        if entry_point not in namespace:
            return False, f'Entry point "{entry_point}" not defined'

        namespace['check'](namespace[entry_point])
        return True, None

    except AssertionError as e:
        return False, f'Test assertion failed: {e}'
    except Exception as e:
        # Include full traceback for debugging
        error_detail = traceback.format_exc()
        return False, f'{type(e).__name__}: {e}\n{error_detail}'


def test_dataset(filepath: Path, task_id_filter: Optional[str] = None) -> Tuple[int, list[dict[str, str]]]:
    """
    Test all canonical solutions in a dataset.

    Args:
        filepath: Path to dataset JSON file
        task_id_filter: Optional task_id to test only that specific problem.
                       If None, tests all problems.

    Returns:
        Tuple of (passed_count, list_of_failures)
        - passed_count: Number of problems that passed
        - failures: List of dicts with 'task_id' and 'error' keys
    """
    try:
        with filepath.open() as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return 0, [{'task_id': 'N/A', 'error': f'Invalid JSON: {e}'}]
    except FileNotFoundError:
        return 0, [{'task_id': 'N/A', 'error': f'File not found: {filepath}'}]

    passed = 0
    failures = []
    found = False

    for idx, problem in enumerate(data):
        task_id = problem.get('task_id', f'unknown_{idx}')

        # If filtering by task_id, skip non-matching problems
        if task_id_filter is not None:
            if task_id != task_id_filter:
                continue
            found = True

        # Validate problem structure first
        required_fields = {'task_id', 'prompt', 'canonical_solution', 'test', 'entry_point'}
        missing = required_fields - set(problem.keys())
        if missing:
            failures.append({
                'task_id': task_id,
                'error': f'Missing required fields: {missing}'
            })
            continue

        # Test the solution
        success, error = test_problem(problem)

        if success:
            passed += 1
        else:
            failures.append({
                'task_id': task_id,
                'error': error
            })

    # If filtering by task_id and not found, return error
    if task_id_filter is not None and not found:
        return 0, [{'task_id': task_id_filter, 'error': f'Task not found in {filepath}'}]

    return passed, failures


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments using argparse.

    Returns:
        Namespace object with parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog='test_solutions.py',
        description='Test canonical solutions against their test cases.',
        epilog='Examples:\n'
               '  python scripts/test_solutions.py\n'
               '  python scripts/test_solutions.py -d dataset/dataset_qiskit_test_human_eval.json\n'
               '  python scripts/test_solutions.py -t qiskitHumanEval/42\n'
               '  python scripts/test_solutions.py -d dataset/dataset_qiskit_test_human_eval.json -t qiskitHumanEval/42',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '-d', '--dataset',
        metavar='<dataset file path>',
        dest='dataset',
        default=None,
        help='Test problems in a specific dataset'
    )

    parser.add_argument(
        '-t', '--task',
        metavar='<problem task id>',
        dest='task',
        default=None,
        help='Test a specific problem (searches all datasets if not combined with -d)'
    )

    return parser.parse_args()


def main() -> int:
    """Run tests on datasets. Optionally filter by dataset file path and/or task_id."""
    # Parse command-line arguments
    args = parse_arguments()

    # Use global failure reporting settings
    global MAX_FAILURES_TO_SHOW, MAX_ERROR_LINES_TO_SHOW

    # Extract arguments and convert to Path objects
    dataset_filter = Path(args.dataset) if args.dataset else None
    task_id_filter = args.task

    # Determine which datasets to test
    default_datasets = [
        Path('dataset/dataset_qiskit_test_human_eval.json'),
        Path('dataset/dataset_qiskit_test_human_eval_hard.json')
    ]

    if dataset_filter:
        # Verify the dataset file exists
        try:
            with dataset_filter.open() as f:
                json.load(f)
            datasets = [dataset_filter]
        except FileNotFoundError:
            print(f'❌ Dataset file not found: {dataset_filter}')
            return 1
        except json.JSONDecodeError as e:
            print(f'❌ Invalid JSON in {dataset_filter}: {e}')
            return 1
    else:
        # If only task_id is specified (no dataset), search all datasets
        # If both task_id and dataset are specified, only search specified dataset
        datasets = default_datasets

    total_passed = 0
    total_failures = []
    dataset_results = {}
    task_found_count = 0

    # Print what we're testing
    if task_id_filter:
        print(f'Testing task: {task_id_filter}')
    if dataset_filter:
        print(f'Dataset: {dataset_filter}')
    if task_id_filter or dataset_filter:
        print()

    for dataset in datasets:
        if task_id_filter:
            print(f'Searching in {dataset}...')
        else:
            print(f'Testing {dataset}...')

        passed, failures = test_dataset(dataset, task_id_filter=task_id_filter)

        dataset_results[dataset] = {
            'passed': passed,
            'total': passed + len(failures),
            'failures': failures
        }

        # Count how many datasets found the task
        if task_id_filter and passed > 0:
            task_found_count += 1

        total_passed += passed
        total_failures.extend([(dataset, f) for f in failures])

        if failures:
            print(f'  ✓ {passed} passed')
            print(f'  ✗ {len(failures)} failed')
        else:
            if passed > 0:
                print(f'  ✓ {passed} passed')

    # Print summary
    total_tested = sum(r['total'] for r in dataset_results.values())

    if task_id_filter:
        if task_found_count > 0:
            print(f'\nResult: {total_passed} passed in {task_found_count} dataset(s)')
            print(f'✅ Task {task_id_filter} PASSED')
        else:
            print('\nResult: Task not found in any dataset')
            print(f'❌ Task {task_id_filter} NOT FOUND')
    elif dataset_filter:
        print(f'\nResults: {total_passed}/{total_tested} solutions passed in {dataset_filter}')
    else:
        print(f'\nResults: {total_passed}/{total_tested} solutions passed')

    if total_failures:
        print(f'\n❌ Testing FAILED ({len(total_failures)} failures):\n')

        for dataset, failure in total_failures[:MAX_FAILURES_TO_SHOW]:
            print(f'{failure["task_id"]} in {dataset}:')
            error_lines = failure['error'].split('\n')
            # Show first N lines of error, then truncate if too long
            for line in error_lines[:MAX_ERROR_LINES_TO_SHOW]:
                print(f'  {line}')
            if len(error_lines) > MAX_ERROR_LINES_TO_SHOW:
                print(f'  ... (truncated, {len(error_lines) - MAX_ERROR_LINES_TO_SHOW} more lines)')
            print()

        if len(total_failures) > MAX_FAILURES_TO_SHOW:
            print(f'... and {len(total_failures) - MAX_FAILURES_TO_SHOW} more failures')

        return 1
    else:
        if task_id_filter:
            print(f'✅ Task {task_id_filter} passed successfully in all datasets')
        elif dataset_filter:
            print(f'✅ All {total_passed} solutions in {dataset_filter} PASSED')
        else:
            print(f'✅ All {total_passed} canonical solutions PASSED')
        return 0


if __name__ == '__main__':
    sys.exit(main())
