# DevAgents ML Datasets

This directory contains the pipeline for building the Phase 8 ML Failure Classifier datasets, fundamentally backed by the real **BugsInPy** benchmark.

## 1. Real Source Dataset
The primary and only source of truth for test evaluation is the **BugsInPy** benchmark (https://github.com/soarsmu/BugsInPy). It contains reproducible defects from real-world Python projects (e.g. pandas, scikit-learn, black).

## 2. Download and Discovery
The `BugsInPy` repository is checked out locally at `<repo_root>/BugsInPy/`. 
The extraction tool (`datasets/bugsinpy/extractor.py`) dynamically traverses `projects/<project_name>/bugs/<bug_id>/bug.info` to discover available bugs across all projects, parsing out metadata such as python_version, buggy_commit_id, and test_file.

## 3. Execution Pipeline (When Environment Permits)
The extraction pipeline relies on the official BugsInPy framework scripts (which require a functional Linux bash environment):
1. **Checkout**: `bugsinpy-checkout -p <project> -i <bug_id> -v 0` targets the buggy commit.
2. **Execution**: `bugsinpy-test` triggers the framework testing wrapper.
3. **Capture**: The process monitors stdout/stderr, exit codes, and durations.
4. **Failure Output**: The raw text output from the test failure is extracted.

## 4. Failure Labeling
Labels are purely derived from the *observed execution failures* using deterministic logic, mapping the thrown Exception to the Phase 7 Debugging taxonomy (e.g. `AssertionError` → `ASSERTION_FAILURE`, `TypeError` → `TYPE_ERROR`). The underlying patch (`bug_patch.txt`) is deliberately ignored during labeling.

## 5. Exclusions and Environmental Blockers
Bugs that fail to run due to missing dependencies, obsolete Python versions, or environmental incompatibilities (e.g., executing bash scripts natively on Windows without a functional WSL distribution) are excluded. 
- **Setup Failures**: Dependencies failed.
- **Unsupported Environment**: e.g., Windows OS missing functional WSL.
*All exclusions are explicitly logged in the extraction manifest (`datasets/bugsinpy/manifests/extraction_manifest.json`).*

## 6. Data Splitting Methodology
Extracted valid failures undergo a **deterministic 80/20 train/test split** (random seed = 42).

## 7. Bug-Level Leakage Prevention
Splits are computed strictly at the *Bug ID* level. If a single bug yields multiple failure samples, they are guaranteed to share the same partition (Train *or* Test). There is zero bug overlap between training and testing.

## 8. Synthetic Augmentation Policy
If (and only if) the real training set is too small or heavily imbalanced, synthetic augmentation is allowed *strictly for the training pool*. 
- Real data has `source = "BugsInPy"`.
- Synthetic data has `source = "synthetic"`.

## 9. Final Test Set Integrity
The final evaluation test set contains **only real BugsInPy samples**. Synthetic examples are never leaked into the test set to inflate metrics.

## 10. ML Model
- **Features**: `TfidfVectorizer(max_features=5000, stop_words="english")`. Fitted exclusively on training data.
- **Classifier**: `LogisticRegression(random_state=42, max_iter=1000)`.

## 11. Evaluation Metrics
Evaluations against the real test set include:
- Accuracy, Confusion Matrix, and Sample Counts.
- Macro and Weighted Precision/Recall/F1 metrics.
- Per-class metrics mapping support vs. precision.

## 12. Reproduction Commands
Run the extractor (requires functional WSL bash if on Windows):
```bash
python -m datasets.bugsinpy.extractor
```
Run the training and evaluation:
```bash
python -m ml.train
```
