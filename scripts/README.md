# Qiskit HumanEval Scripts

This directory contains utility scripts for dataset validation and testing.

## Security Notice

⚠️ **Important:** The `test_solutions.py` script executes code from the dataset using Python's `exec()` function. This is safe **only** when used with trusted, version-controlled sources. See the `test_solutions.py` section below for detailed security information and safe usage guidelines.

## Available Scripts

### `validate_dataset.py`
Validates the structure and content of dataset JSON files.

**Usage:**
```bash
python scripts/validate_dataset.py
```

**What it checks:**
- Valid JSON syntax
- Required fields present (task_id, prompt, canonical_solution, test, entry_point, difficulty_scale)
- Valid difficulty scales (basic, intermediate, difficult)
- Correct task_id format (must start with qiskitHumanEval/)
- No empty required fields
- No duplicate task_ids

**Output:**
- Success: Returns 0, prints summary of validated problems
- Failure: Returns 1, prints detailed errors to fix

**Example success output:**
```
Validating dataset/dataset_qiskit_test_human_eval.json...
  ✓ 151 problems found
Validating dataset/dataset_qiskit_test_human_eval_hard.json...
  ✓ 151 problems found

✅ Dataset validation PASSED
✓ 302 total problems validated
✓ All required fields present
✓ No duplicate task_ids
✓ Valid difficulty scales
```

**Example failure output:**
```
Validating dataset/dataset_qiskit_test_human_eval.json...
  ✓ 151 problems found

❌ Dataset validation FAILED:

dataset/dataset_qiskit_test_human_eval.json:
  - Problem 5 (qiskitHumanEval/5): Missing fields {'canonical_solution'}
  - Problem 10 (qiskitHumanEval/10): Invalid difficulty_scale "hard" (must be basic, intermediate, or difficult)
```

### `test_solutions.py`
Tests that all canonical solutions pass their corresponding test cases.

**⚠️ SECURITY WARNING: Code Execution**

This script uses Python's `exec()` function to execute code from the dataset. This is potentially dangerous and should only be used with **trusted, version-controlled code sources**.

**Safe usage (this project):**
- ✅ Dataset is version-controlled in Git
- ✅ All changes require code review before merge
- ✅ Runs only on trusted developer/CI systems
- ✅ No untrusted user input

**DO NOT use with:**
- ❌ User-submitted code
- ❌ Untrusted data sources
- ❌ Network-provided solutions
- ❌ Unreviewed changes


**Requires:** Dependencies from `requirements.txt` (qiskit, etc.)

**Usage:**
```bash
python scripts/test_solutions.py [options]

Options:
  -d <dataset file path>     Test problems in a specific dataset
  -t <problem task id>       Test a specific problem
```

**What it does:**
- Loads each problem from datasets
- Executes: prompt + canonical_solution + test
- Runs the check() function against the solution
- Reports pass/fail for each problem
- Fails if any canonical solution doesn't pass its test

**Output:**
- Success: Returns 0, prints summary of test results
- Failure: Returns 1, prints detailed errors with first 10 failures

**Example success output:**
```
Testing dataset/dataset_qiskit_test_human_eval.json...
  ✓ 151 passed
Testing dataset/dataset_qiskit_test_human_eval_hard.json...
  ✓ 151 passed

Results: 302/302 solutions passed
✅ All 302 canonical solutions PASSED
```

**Example failure output:**
```
Testing dataset/dataset_qiskit_test_human_eval.json...
  ✓ 149 passed
  ✗ 2 failed

Results: 149/151 solutions passed

❌ Testing FAILED (2 failures):

qiskitHumanEval/5 in dataset/dataset_qiskit_test_human_eval.json:
  AssertionError: assert result == expected
  Traceback (most recent call last):
    ...

qiskitHumanEval/42 in dataset/dataset_qiskit_test_human_eval.json:
  ValueError: Invalid quantum state
  ...
```

## Running Before Commits

Before pushing dataset changes, run validation and tests locally:

```bash
# 1. Validate datasets structure
python scripts/validate_dataset.py

# 2. Test canonical solutions (if Qiskit is installed)
python scripts/test_solutions.py

# If both succeed, proceed with commit
git add dataset/
git commit -m "Add new problems to dataset"
git push
```

## CI/CD Integration

This script is automatically called by GitHub Actions workflows:
- `.github/workflows/validate-dataset.yml` → calls `validate_dataset.py`
  - Runs on: dataset file changes
  - Installs: Only Python (no dependencies needed)

## Adding New Scripts

When adding new validation or testing scripts:
1. Place in this `scripts/` directory
2. Add shebang: `#!/usr/bin/env python3`
3. Include docstring explaining usage
4. Use `if __name__ == '__main__'` entry point
5. Return appropriate exit codes (0 = success, 1 = failure)
6. Update this README with usage instructions
