# NYC 311 City Service Request Analytics: Portal / Data Setup

This folder covers the **Portal/data setup** part of project 6. It delivers the documented,
reproducible dataset and the environment for team to build on.

## Contents

| Path | Purpose |
|---|---|
| `config/dataset_config.json` | Single source of truth: dataset ID, filters, CSV path, required columns |
| `DATA_SOURCE.md` | Official source, exact filters, export facts, limitations (fill in `[]`) |
| `PORTAL_FILTER_STEPS.md` | Step-by-step export instructions and checklist |
| `scripts/check_environment.py` | Checks Python 3.11+, NumPy, Matplotlib |
| `scripts/build_export_url.py` | Prints the exact SoQL filter and export URL from the config |
| `scripts/verify_dataset.py` | Confirms the CSV matches the documented filters (row count, SHA-256, date range, rows outside filters) and writes the provenance manifest |
| `provenance/` | Screenshot / saved filter description and `dataset_manifest.json` |
| `data/raw/` | The exported CSV (not included) |
| `requirements.txt` | Python dependencies |

## Workflow

```
pip install -r requirements.txt
python scripts/check_environment.py
python scripts/build_export_url.py        # or follow docs/PORTAL_FILTER_STEPS.md
# download the CSV into data/raw/ and add the screenshot / filter description to provenance/
python scripts/verify_dataset.py
# copy the measured values into DATA_SOURCE.md
```

## Hand-off to the other team members

- Parser/indexing: read `config/dataset_config.json` for the CSV path and column names.
  Portal headers may use either backend names (`complaint_type`) or labels ("Problem");
  `verify_dataset.py` shows how to map both.
- Analytics/plots: use only the frozen CSV; never re-download during analysis (offline requirement).
- Validation/documentation: `dataset_manifest.json` gives the verified row count and SHA-256 as a starting cross-check. The data-quality report (duplicate IDs, malformed timestamps, open/closed/missing status) is NOT produced here; it is built by the parser/validation parts.


## Rules the team must follow

- Never invent, edit by hand, or replace data silently
- Any change to the slice means: update the config, re-export, re-verify, update `DATA_SOURCE.md`.
