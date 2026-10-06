# DevAgents ML Datasets

This directory (or equivalent remote storage) contains datasets used for training the Phase 8 ML Failure Classifier.

## BugsInPy Derived Dataset

The initial dataset is derived from a subset of [BugsInPy](https://github.com/soarsmu/BugsInPy), simulating realistic test failure scenarios in Python codebases (such as pandas, scipy, scikit-learn).

### Label Taxonomy

The labels are aligned with the existing Phase 7 Debugging taxonomy:
- SYNTAX_ERROR
- IMPORT_ERROR
- DEPENDENCY_ERROR
- TYPE_ERROR
- ATTRIBUTE_ERROR
- NAME_ERROR
- VALUE_ERROR
- ASSERTION_FAILURE
- RUNTIME_ERROR
- TIMEOUT
- UNKNOWN_ERROR

### Preprocessing
1. Extraction of `stdout`, `stderr`, and test execution `command`.
2. Removal of absolute and relative file paths (to prevent model memorization/overfitting on project-specific structures).
3. Removal of hexadecimal memory addresses (e.g., `0x7f8b9c...`).
4. Removal of specific line numbers (e.g., `line 42`).
5. Conversion to lowercase, retention of alphanumeric and basic punctuation (.,-_), and stripping extraneous whitespace.

### Labeling Methodology
For this initial iteration, errors are labeled based on the explicit `Exception` string found in the traceback (e.g., `AssertionError` -> `ASSERTION_FAILURE`, `TypeError` -> `TYPE_ERROR`). Where the explicit class is not available or ambiguous, `RUNTIME_ERROR` or `UNKNOWN_ERROR` is utilized.

### Split Methodology
- A deterministic Random Seed (default 42).
- Test Size: 20%.
- Stratified sampling is used when class populations permit.

### Limitations
- The synthetic/subset representation currently used for Phase 8 might not capture the full breadth of multi-file semantic logic errors (`LOGIC_ERROR`), which often manifest as standard `AssertionError`s without an explicit Python exception.
- Highly imbalanced classes (e.g. `TIMEOUT`) will exhibit skewed precision/recall metrics.
