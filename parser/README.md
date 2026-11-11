# NYC 311 City Service Request Analytics: Parser / Indexing

This folder covers the **Parser/indexing** part of project 6. It reads the raw 311 CSV, indexes
every request by its `unique_key`, checks data quality, reports request statuses, and exports a
clean CSV for the analytics part to use.

## Contents

| File                      | What it is              |
|:--------------------------|:------------------------|
| `script/parser.py`        | The parser script       |
| `data/cleaned_data*.csv`  | Clean data export       |
| `data/quality_report.txt` | Status + quality report |

> Files in `data/` are overwritten every time the parser runs.

## What the parser does

1. **Loads and indexes** the raw CSV (`portal_data_setup/data/nyc311_brooklyn_2026-07.csv` by default)
   into a dictionary keyed by `unique_key`. Each row becomes a `ServiceRequest` object.
2. **Reports statuses** in three groups, plus a breakdown by the raw status value:

   | Group       | Includes these statuses                                  |
   |:------------|:---------------------------------------------------------|
   | **Open**    | `Open` · `In Progress` · `Assigned` · `Started` · `Pending` |
   | **Closed**  | `Closed`                                                 |
   | **Missing** | *(empty)* · `Unspecified`                                |

   Any other status value not listed here is counted as **Open**.

3. **Checks data quality** and lists every affected ID in the report:

   | Check                 | Problem                              | In clean CSV?     |
   |:----------------------|:-------------------------------------|:------------------|
   | Missing ID            | Row has no `unique_key`              | ❌ Removed        |
   | Duplicate ID          | Same `unique_key` appears again      | ⚠️ First copy kept |
   | Unparseable date      | Not `YYYY-MM-DDTHH:MM:SS.fff` format | ❌ Removed        |
   | Closed before created | `closed_date` < `created_date`       | ❌ Removed        |
   | Closed without date   | Status `Closed`, no `closed_date`    | ✅ Kept           |

4. **Filters** by agency, problem type (`complaint_type`) and/or status, if requested.
5. **Exports** the clean records and the report to `parser/data/`. Old `cleaned_data*.csv` files
   are deleted first, so the folder always holds only the latest run.

## How to use

Complete the setup in the main [`README.md`](../README.md) first (Python 3.11+, verified dataset).
The commands below can be run from any folder; paths are resolved from the script's location.

**Process the whole dataset (no filter):**

```
python parser/script/parser.py
```

**See which values you can filter by:**

```
python parser/script/parser.py --list agency
python parser/script/parser.py --list problem-type
python parser/script/parser.py --list status
```

**Filter by agency, problem type or status** (matching ignores upper/lower case; filters can be combined):

```
python parser/script/parser.py --agency DSNY
python parser/script/parser.py --problem-type "Abandoned Bike"
python parser/script/parser.py --agency DSNY --problem-type "Abandoned Bike"
python parser/script/parser.py --status "In Progress"
```

Put values containing spaces in quotes. If a filter matches nothing, the parser warns you; use `--list` to check spelling.

**Choose a filter from a menu instead of flags:**

```
python parser/script/parser.py --interactive
```

**Use a different input file:**

```
python parser/script/parser.py --input path/to/other.csv
```

Run `python parser/script/parser.py --help` for the full option list.

## Output

The same report is printed to the console and saved to `parser/data/quality_report.txt`:

```
=== DATA QUALITY REPORT ===
Total unique records parsed : 104,867
Duplicate IDs found         : 0
Unparseable timestamps      : 0
Closed before created       : 11
Closed without closed_date  : 1

=== STATUS REPORT (all records) ===
Open records                : 5,795
Closed records              : 99,069
Missing-status records      : 3
  Breakdown by raw status: ...
```

When a filter is used, a `FILTER RESULTS` section with the matching count and its status
breakdown is added. The text file also lists every faulty ID under each quality check.

The clean CSV is named after the filter, for example:

| Filter used                         | Saved in `parser/data/` as                       |
|:------------------------------------|:-------------------------------------------------|
| *(none)*                            | `cleaned_data.csv`                               |
| `--agency DSNY`                     | `cleaned_data_agency_dsny.csv`                   |
| `--problem-type "Abandoned Bike"`   | `cleaned_data_problem_type_abandoned_bike.csv`   |

Columns: `unique_key, agency, complaint_type, borough, status, created_date, closed_date`.

**For the analytics part:** run the parser with no filter and read `parser/data/cleaned_data.csv`.
It contains every unique record with valid timestamps (104,856 rows for the July 2026 Brooklyn slice).

## Using it from Python

```python
from parser import RequestIndex   # run from parser/script/, or add it to sys.path

index = RequestIndex("portal_data_setup/data/nyc311_brooklyn_2026-07.csv")
index.load_and_index()

dsny = index.filter_records(agency="DSNY")
print(RequestIndex.status_summary(dsny)["groups"])   # Counter({'closed': ..., 'open': ...})
```

Each `ServiceRequest` has `created_dt` / `closed_dt` as parsed `datetime` objects (or `None`),
which can be used directly for closure-time calculations.
