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
- ✅ 30-second timeout protection per test
- ✅ Isolated namespace execution
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
  -d, --dataset <path>       Test problems in a specific dataset
  -t, --task <task_id>       Test a specific problem (searches all datasets)
  -e, --exclude-prompt       Exclude prompt from execution (for specific dataset)
  -v, --verbose              Enable detailed logging
  -o, --output <file>        Write JSON results to file (use "stdout" or "-" to pipe)
  -h, --help                 Show help message
```

**Basic Examples:**
```bash
# Test all datasets
python scripts/test_solutions.py

# Test specific dataset
python scripts/test_solutions.py -d dataset/dataset_qiskit_test_human_eval.json

# Test specific task across all datasets
python scripts/test_solutions.py -t qiskitHumanEval/42

# Verbose output for debugging
python scripts/test_solutions.py -v

# Exclude prompt from execution
python scripts/test_solutions.py -e -d dataset/custom.json

# Save results to JSON file
python scripts/test_solutions.py -o results.json

# Combine options
python scripts/test_solutions.py -v -d dataset/custom.json -o results.json

# Extract only failures
python scripts/test_solutions.py -o stdout | jq '.failures[] | .task_id'

# Calculate pass rate
python scripts/test_solutions.py -o stdout | \
  jq '.summary.total_passed / .summary.total_tested * 100'
```

**JSON Output Format:**
```json
{
  "summary": {
    "total_passed": 160,
    "total_tested": 164,
    "total_failed": 4,
    "success": false,
    "execution_time_seconds": 45.23
  },
  "filters": {
    "dataset": null,
    "task_id": null,
    "exclude_prompt": false
  },
  "datasets": {
    "dataset/dataset_qiskit_test_human_eval.json": {
      "passed": 160,
      "total": 161,
      "failed": 1
    }
  },
  "failures": [
    {
      "task_id": "qiskitHumanEval/42",
      "dataset": "dataset/dataset_qiskit_test_human_eval.json",
      "error": "Test assertion failed: ...",
      "code": "def solution():\n    ..."
    }
  ]
}
```

**What it does:**
- Loads each problem from datasets
- Executes: prompt + canonical_solution + test (with 30s timeout)
- Runs the check() function against the solution
- Reports pass/fail for each problem
- Tracks execution time
- Optionally outputs structured JSON

**Security Features:**
- ⏱️ 30-second timeout per test (prevents infinite loops)
- 🔒 Isolated namespace execution with restricted builtins
  - Blocks dangerous functions: `eval()`, `exec()`, `compile()`, `breakpoint()`, `input()`
  - Allows legitimate imports via `__import__` (required for `import` statements)
- 📝 Comprehensive logging
- 🛡️ CI/CD hardening: read-only permissions, deterministic hashing, no bytecode caching

**Output:**
- Success: Returns 0, prints summary of test results
- Failure: Returns 1, prints detailed errors
- JSON: Optionally writes structured results to file or stdout

**Example success output:**
```
2026-02-25 00:15:23 - INFO     - Starting test_solutions.py
2026-02-25 00:15:23 - INFO     - Using default datasets: ['dataset/dataset_qiskit_test_human_eval.json', 'dataset/dataset_qiskit_test_human_eval_hard.json']
2026-02-25 00:15:23 - INFO     - Loading dataset: dataset/dataset_qiskit_test_human_eval.json
2026-02-25 00:15:45 - INFO     - Dataset dataset/dataset_qiskit_test_human_eval.json: 164 passed, 0 failed
2026-02-25 00:16:07 - INFO     - Dataset dataset/dataset_qiskit_test_human_eval_hard.json: 164 passed, 0 failed
2026-02-25 00:16:07 - INFO     - Total execution time: 44.12 seconds
2026-02-25 00:16:07 - INFO     - Results: 328/328 passed
2026-02-25 00:16:07 - INFO     - All 328 canonical solutions passed
```

**Example failure output:**
```
2026-02-25 00:15:23 - INFO     - Starting test_solutions.py
2026-02-25 00:15:45 - INFO     - Dataset dataset/dataset_qiskit_test_human_eval.json: 162 passed, 2 failed
2026-02-25 00:15:45 - INFO     - Total execution time: 22.34 seconds
2026-02-25 00:15:45 - INFO     - Results: 162/164 passed
2026-02-25 00:15:45 - INFO     - Testing failed with 2 failure(s)

    qiskitHumanEval/5 in dataset/dataset_qiskit_test_human_eval.json:
      Test assertion failed: assert result == expected
      Traceback (most recent call last):
        File "<string>", line 45, in check
      AssertionError

    qiskitHumanEval/42 in dataset/dataset_qiskit_test_human_eval.json:
      Execution timeout: Execution exceeded 30 seconds
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

## Troubleshooting

### Common Issues

**Issue: "ModuleNotFoundError: No module named 'qiskit'"**
```bash
# Solution: Install dependencies
pip install -r requirements.txt
```

**Issue: "Execution timeout" errors**
- Some problems may have inefficient solutions
- 30-second timeout is intentional to prevent infinite loops
- Review the solution code for optimization opportunities

**Issue: JSON output not working**
```bash
# Ensure you're using correct syntax
python scripts/test_solutions.py -o results.json  # File output
python scripts/test_solutions.py -o stdout        # Stdout output
python scripts/test_solutions.py -o -             # Stdout output (Unix style)
```

**Issue: Verbose mode not showing output**
```bash
# Verbose mode is suppressed when using stdout JSON output
python scripts/test_solutions.py -v               # Works
python scripts/test_solutions.py -v -o stdout     # Verbose suppressed (by design)
```

### Performance Tips

- Use `-t` flag to test specific problems during development
- Use `-d` flag to test one dataset at a time
- Verbose mode (`-v`) adds minimal overhead
- JSON output to file is faster than stdout piping

## CI/CD Integration

These scripts are automatically called by GitHub Actions workflows on every push and pull request that modifies files under `dataset/`:

### Validation Workflow
- `.github/workflows/validate-dataset.yml` → calls `validate_dataset.py`
  - Runs on: `dataset/**` changes (push to `main`, PRs targeting `main`)
  - Installs: Only Python (no extra dependencies needed)
  - Purpose: Validates JSON structure and required fields

### Test Solutions Workflow
- `.github/workflows/test-solutions.yml` → calls `test_solutions.py`
  - Runs on: `dataset/**` changes (push to `main`, PRs targeting `main`)
  - Installs: Python + all dependencies from `requirements.txt` (Qiskit, etc.)
  - Purpose: Executes all canonical solutions against their test cases to verify correctness
  - Runtime: ~45 seconds for the full dataset
  - Exit code: `0` (all pass) or `1` (one or more failures) — blocks PR merge on failure

## Adding New Scripts

When adding new validation or testing scripts:
1. Place in this `scripts/` directory
2. Add shebang: `#!/usr/bin/env python3`
3. Include docstring explaining usage
4. Use `if __name__ == '__main__'` entry point
5. Return appropriate exit codes (0 = success, 1 = failure)
6. Update this README with usage instructions
