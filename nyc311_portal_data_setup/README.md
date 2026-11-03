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
| `data/` | The exported CSV (not included) |
| `requirements.txt` | Python dependencies |

## Workflow

```
pip install -r requirements.txt
python scripts/check_environment.py
python scripts/build_export_url.py        # or follow docs/PORTAL_FILTER_STEPS.md
# download the CSV into data/ and add the screenshot or filter description to provenance/
python scripts/verify_dataset.py
# copy the measured values into DATA_SOURCE.md
```


## Rules the team must follow

- Never invent, edit by hand, or replace data silently
- Any change to the slice means: update the config, re-export, re-verify, update `DATA_SOURCE.md`.
