# Analytics & Visualization Module

This module handles numerical aggregations and offline data visualization for the NYC 311 dataset using **NumPy** and **Matplotlib**.

## Module Structure

- `inspect_data.py` — Helper utilities to preview data structure and counts.
- `statistics.py` — Core statistical engine (NumPy) computing rankings, status breakdowns, and valid closure-time metrics.
- `visualizations.py` — Plotting script (Matplotlib) rendering charts to `output/`.

## Usage

Run from the project root directory:

```
python analytics/statistics.py
python analytics/visualizations.py
```

## Outputs (`output/`)

- **Reports:** `summary_report.txt`, `complaint_type_counts.csv`, `agency_counts.csv`, `agency_comparison.csv`
- **Plots:** `complaint_types.png`, `agencies.png`, `agency_request_comparison.png`, `agency_closure_time_comparison.png`, `daily_requests.png`, `status_distribution.png`