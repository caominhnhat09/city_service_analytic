# NYC 311 City Service Request Analytics

Course project 6. The team analyzes a real municipal service-request dataset (NYC 311 Service
Requests from 2020 to Present) and builds an offline dashboard that shows which types of
requests were reported, which agencies handled them, and how closure times vary.



## Requirements

- Python 3.11 or newer
- NumPy and Matplotlib



## Setup

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Check the environment:

   ```
   python check_environment.py
   ```

   All lines should show `[OK]`.



## Dataset

The team uses one fixed slice of the NYC 311 dataset so that everyone analyzes exactly the same file.

- Source, dataset ID, exact portal filters and export details: [`portal_data_setup/DATA_SOURCE.md`]
- How the CSV was exported and verified: [`portal_data_setup/README.md`]
- Configuration (filters and CSV path): [`portal_data_setup/config/dataset_config.json`]

To confirm you have the same file as the team, run `python portal_data_setup/scripts/verify_dataset.py` and compare the SHA-256 with `DATA_SOURCE.md`.

Never invent, edit by hand, or replace data silently. If the slice has to be changed, update the configuration, update `portal_data_setup/PORTAL_FILTER_STEPS.md`, re-export, re-verify and update `portal_data_setup/DATA_SOURCE.md`.





## Parser / indexing

The parser reads the raw CSV, indexes requests by `unique_key`, reports open / closed /
missing-status counts, flags duplicate IDs and malformed timestamps, and exports a clean CSV
plus a quality report to `parser/data/`.

```
python parser/script/parser.py                                 # whole dataset
python parser/script/parser.py --agency DSNY                   # filter by agency
python parser/script/parser.py --problem-type "Abandoned Bike" # filter by problem type
python parser/script/parser.py --list agency                   # show valid filter values
```

Full guide: [`parser/README.md`](parser/README.md)



... (analytics, validation should fill appropriately in README.MD later) ...





## Team rules

- Never edit the raw CSV by hand.
- Keep paths and filters in configuration files, not hard-coded in the code.
- Analysis code must not use the network.