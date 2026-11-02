import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "dataset_config.json"
MANIFEST_PATH = ROOT / "provenance" / "dataset_manifest.json"
DATA_SOURCE_PATH = ROOT / "DATA_SOURCE.md"
PLACEHOLDER = "[]"

HEADER_ALIASES = {
    "unique_key": {"unique_key"},
    "created_date": {"created_date"},
    "closed_date": {"closed_date"},
    "agency": {"agency"},
    "complaint_type": {"complaint_type", "problem", "problem_formerly_complaint_type"},
    "status": {"status"},
    "borough": {"borough"},
}

# Only used to locate the date window; full timestamp parsing belongs to the parser.
CREATED_DATE_FORMATS = ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %I:%M:%S %p")


def normalize_header(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def locate_columns(header: list[str]) -> dict[str, int]:
    """Return {canonical_name: column_index} for the columns this script knows."""
    found: dict[str, int] = {}
    for index, raw in enumerate(header):
        norm = normalize_header(raw)
        for canonical, aliases in HEADER_ALIASES.items():
            if norm in aliases and canonical not in found:
                found[canonical] = index
    return found


def parse_created(text: str) -> datetime | None:
    """Return a datetime, or None if blank/unreadable (the row is then not date-checked)."""
    text = text.strip()
    for fmt in CREATED_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True: 
            block = handle.read(1024 * 1024)
            if block == b"":
                break
            digest.update(block)
    return digest.hexdigest()


def check_slice(csv_path: Path, config: dict) -> dict:
    filters = config["filters"]
    window_start = datetime.fromisoformat(filters["created_date_start_inclusive"])
    window_end = datetime.fromisoformat(filters["created_date_end_exclusive"])
    expected_borough = (filters.get("borough") or "").strip().upper()

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        columns = locate_columns(header)
        missing = [c for c in config["required_columns"] if c not in columns]
        if missing:
            return {"header": header, "missing_columns": missing}

        created_index = columns["created_date"]
        borough_index = columns["borough"]
        rows = outside_window = outside_borough = unreadable = 0
        min_created = max_created = None

        for row in reader:
            if not any(cell.strip() for cell in row):
                continue
            rows += 1

            created = parse_created(row[created_index]) if created_index < len(row) else None
            if created is None:
                unreadable += 1
            else:
                min_created = created if min_created is None else min(min_created, created)
                max_created = created if max_created is None else max(max_created, created)
                if not (window_start <= created < window_end):
                    outside_window += 1

            if expected_borough:
                borough = row[borough_index].strip().upper() if borough_index < len(row) else ""
                if borough != expected_borough:
                    outside_borough += 1

    return {
        "header": header,
        "missing_columns": [],
        "rows": rows,
        "rows_outside_created_window": outside_window,
        "rows_outside_borough": outside_borough,
        "rows_with_unreadable_created_date": unreadable,
        "created_min": min_created.isoformat() if min_created else None,
        "created_max": max_created.isoformat() if max_created else None,
    }


def main() -> int:
    
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    csv_path = (ROOT / config["csv_path"])

    if not csv_path.is_file():
        print(f"[FAIL] CSV not found: {csv_path}")
        print("       Check 'csv_path' in config/dataset_config.json, or export the file first "
              "(see docs/PORTAL_FILTER_STEPS.md).")
        return 1

    result = check_slice(csv_path, config)
    if result["missing_columns"]:
        print(f"[FAIL] Missing required columns: {result['missing_columns']}")
        print(f"       Header found: {result['header']}")
        return 1
    if result["rows"] == 0:
        print("[FAIL] The CSV has a header but no data rows.")
        return 1

    manifest = {
        "verified_at": datetime.now().isoformat(timespec="seconds"),
        "csv_file": csv_path.name,
        "csv_size_bytes": csv_path.stat().st_size,
        "csv_sha256": sha256_of(csv_path),
        "dataset_id": config["dataset_id"],
        "filters": config["filters"],
        "columns_in_file": result["header"],
        "rows": result["rows"],
        "rows_outside_created_window": result["rows_outside_created_window"],
        "rows_outside_borough": result["rows_outside_borough"],
        "rows_with_unreadable_created_date": result["rows_with_unreadable_created_date"],
        "created_min_in_file": result["created_min"],
        "created_max_in_file": result["created_max"],
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"File:                         {csv_path.name}")
    print(f"SHA-256:                      {manifest['csv_sha256']}")
    print(f"Rows:                         {manifest['rows']}")
    print(f"Created range in file:        {manifest['created_min_in_file']}  ->  {manifest['created_max_in_file']}")
    print(f"Rows outside date window:     {manifest['rows_outside_created_window']}")
    print(f"Rows outside borough filter:  {manifest['rows_outside_borough']}")
    if manifest["rows_with_unreadable_created_date"]:
        print(f"Rows with unreadable Created Date (not date-checked): "
              f"{manifest['rows_with_unreadable_created_date']}  <-- pass to the validation owner")

    problems = manifest["rows_outside_created_window"] or manifest["rows_outside_borough"]
    if problems:
        print("\n[WARN] Some rows do not match the documented filters. Re-export, or document why.")

    if DATA_SOURCE_PATH.is_file() and PLACEHOLDER in DATA_SOURCE_PATH.read_text(encoding="utf-8"):
        print(f"\n[WARN] DATA_SOURCE.md still contains {PLACEHOLDER} placeholders. "
              "Fill them in with the values above (undocumented data is a major defect).")

    print(f"\nManifest written to {MANIFEST_PATH.relative_to(ROOT)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
