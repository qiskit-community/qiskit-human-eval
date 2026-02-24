#!/usr/bin/env python3
"""Validate Qiskit HumanEval dataset structure and content."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Tuple


def validate_dataset(filepath: Path) -> Tuple[Optional[int], list[str]]:
    """
    Validate dataset JSON structure and content.

    Args:
        filepath: Path to dataset JSON file

    Returns:
        Tuple of (problem_count, list_of_errors)
        - problem_count: Number of problems if valid, None if file error
        - errors: List of error strings, empty if all valid
    """
    try:
        with filepath.open() as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return None, [f'Invalid JSON: {e}']
    except FileNotFoundError:
        return None, [f'File not found: {filepath}']

    required_fields = {
        'task_id',
        'prompt',
        'canonical_solution',
        'test',
        'entry_point',
        'difficulty_scale'
    }
    valid_difficulties = {'basic', 'intermediate', 'difficult'}
    errors = []

    for idx, problem in enumerate(data):
        # Check required fields
        missing = required_fields - set(problem.keys())
        if missing:
            errors.append(
                f'Problem {idx} ({problem.get("task_id", "unknown")}): '
                f'Missing fields {missing}'
            )

        # Check difficulty scale
        if problem.get('difficulty_scale') not in valid_difficulties:
            errors.append(
                f'Problem {idx}: Invalid difficulty_scale '
                f'"{problem.get("difficulty_scale")}" '
                f'(must be basic, intermediate, or difficult)'
            )

        # Check task_id format
        task_id = problem.get('task_id', '')
        if not task_id.startswith('qiskitHumanEval/'):
            errors.append(
                f'Problem {idx}: Invalid task_id format "{task_id}" '
                f'(must start with qiskitHumanEval/)'
            )

        # Check for empty fields
        for field in required_fields:
            if not str(problem.get(field, '')).strip():
                errors.append(
                    f'Problem {idx} ({problem.get("task_id", "unknown")}): '
                    f'Empty {field}'
                )

    # Check for duplicates
    task_ids = [p.get('task_id') for p in data]
    duplicates = [tid for tid in set(task_ids) if task_ids.count(tid) > 1]
    if duplicates:
        errors.append(f'Duplicate task_ids found: {duplicates}')

    return len(data), errors


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments using argparse.

    Returns:
        Namespace object with parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog='validate_dataset.py',
        description='Validate Qiskit HumanEval dataset structure and content.',
        epilog='Examples:\n'
               '  python scripts/validate_dataset.py\n'
               '  python scripts/validate_dataset.py -d dataset/dataset_qiskit_test_human_eval.json',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '-d', '--dataset',
        metavar='<dataset file path>',
        dest='dataset',
        default=None,
        help='Validate a specific dataset'
    )

    return parser.parse_args()


def main() -> int:
    """Run validation on datasets."""
    # Parse command-line arguments
    args = parse_arguments()

    # Determine which datasets to validate
    if args.dataset:
        datasets = [Path(args.dataset)]
    else:
        datasets = [
            Path('dataset/dataset_qiskit_test_human_eval.json'),
            Path('dataset/dataset_qiskit_test_human_eval_hard.json')
        ]

    all_errors = {}
    total_problems = 0

    for dataset in datasets:
        print(f'Validating {dataset}...')
        count, errors = validate_dataset(dataset)

        if count is not None:
            total_problems += count
            print(f'  ✓ {count} problems found')

        if errors:
            all_errors[dataset] = errors

    if all_errors:
        print('\n❌ Dataset validation FAILED:\n')
        for dataset, errors in all_errors.items():
            print(f'{dataset}:')
            for error in errors:
                print(f'  - {error}')
        return 1
    else:
        print('\n✅ Dataset validation PASSED')
        print(f'✓ {total_problems} total problems validated')
        print('✓ All required fields present')
        print('✓ No duplicate task_ids')
        print('✓ Valid difficulty scales')
        return 0


if __name__ == '__main__':
    sys.exit(main())
