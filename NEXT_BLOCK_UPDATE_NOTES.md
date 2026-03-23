# Next Block Update

This package advances the unified pool service platform with an estimate workspace layer while preserving the estimator features that were added earlier.

Included in this block:
- commercial estimator preserved and upgraded
- separate chemical pricing preserved
- save, print, PDF, HTML, and JSON export preserved
- saved estimate library page added
- compare saved runs added
- load saved estimate back into Commercial Estimator as a draft
- delete saved estimate run added
- estimate API expanded for saved runs, report access, compare, and delete

Files updated in this block:
- `app/services/estimator.py`
- `app/services/estimate_reporting.py`
- `app/services/estimate_workspace.py`
- `app/api/routes/estimates.py`
- `ui/pages/5_Commercial_Estimator.py`
- `ui/pages/10_Estimate_Library.py`
- `tests/test_estimate_workspace_features.py`

Validation performed here:
- syntax compilation passed for the updated files
- unit test execution could not be completed in this container because the runtime here does not have project dependencies like `sqlmodel` installed globally
