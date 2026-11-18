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

- **Reports:** `complaint_type_counts.csv`, `agency_counts.csv`, `closure_time.txt`
- **Plots:** `complaint_types.png`, `agencies.png`, `compare.png`, `daily_requests.png`