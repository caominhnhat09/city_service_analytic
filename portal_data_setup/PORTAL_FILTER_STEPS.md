# Portal filter and export steps

Goal: create the team CSV from NYC Open Data using documented filters, so anyone can reproduce it.
The values below come from `config/dataset_config.json`.

## Option A: portal user interface

1. Open the dataset page (link in `DATA_SOURCE.md`, section 1).
2. Click the **Data** section.
3. In **Created Date** column: add filter **Created Date** is on or after `07/01/2026`, add filter: **Created Date** is before `08/01/2026`.
4. In **Borough** column: add filter **Borough** is `BROOKLYN`.
5. Check the row count shown by the portal. Keep it under the configured limit.
6. Take a **screenshot of the page showing all active filters and the row count** and save it as `provenance/portal_filters_screenshot.png`.
7. Click **Export** and choose **CSV**. Save as `data/nyc311_brooklyn_2026-07.csv`.

## Option B: API URL

1. Run `scripts/build_export_url.py`.
2. Open the printed URL in a browser (or use any download tool) and save the CSV as `data/nyc311_brooklyn_2026-07.csv`.
3. Save the printed SoQL filter in `provenance/saved_filter_description.txt`

## After the export (both options)

1. Run `scripts/verify_dataset.py`
2. Copy the values from `provenance/dataset_manifest.json` into `DATA_SOURCE.md`.
3. Make sure no `[]` remains in `DATA_SOURCE.md`.
4. Share the CSV and its SHA-256 with the team. Nobody should re-export without updating the hash.

