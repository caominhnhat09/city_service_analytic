import csv
import argparse
from pathlib import Path
from datetime import datetime
from collections import Counter

import numpy as np


# Project paths
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_DIR / "parser" / "data" / "cleaned_data.csv"
OUTPUT_DIR = PROJECT_DIR / "output"


def parse_date(value):
    """Convert a timestamp into datetime."""
    if not value or not value.strip():
        return None

    try:
        return datetime.fromisoformat(value.strip())
    except ValueError:
        return None


def load_data(file_path):
    """Load CSV records."""
    with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader)


def filter_data(records, complaint_type=None, agency=None):
    """Filter records by complaint type or agency."""
    filtered = records

    if complaint_type:
        filtered = [
            row for row in filtered
            if row.get("complaint_type", "").strip().lower()
            == complaint_type.lower()
        ]

    if agency:
        filtered = [
            row for row in filtered
            if row.get("agency", "").strip().lower()
            == agency.lower()
        ]

    return filtered


def analyze_data(records):
    """Calculate statistics for complaint types, agencies, and closure times."""
    complaints = Counter()
    agencies = Counter()
    closure_times = []
    daily_requests = Counter()

    for row in records:
        # Count complaint types
        complaint = row.get("complaint_type", "").strip()
        complaints[complaint or "Unknown"] += 1

        # Count agencies
        agency = row.get("agency", "").strip()
        agencies[agency or "Unknown"] += 1

        # Parse timestamps
        created = parse_date(row.get("created_date", ""))
        closed = parse_date(row.get("closed_date", ""))

        if created is not None:
            daily_requests[created.date().isoformat()] += 1

        # Calculate closure time only when both dates are valid and non-negative
        if created and closed:
            duration = (closed - created).total_seconds() / 3600

            if duration >= 0:
                closure_times.append(duration)

    # NumPy calculations
    if closure_times:
        values = np.array(closure_times)
        q1, q3 = np.percentile(values, [25, 75])

        closure_stats = {
            "count": len(values),
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "variance": float(np.var(values)),
            "std_dev": float(np.std(values)),
            "q1": float(q1),
            "q3": float(q3),
            "min": float(np.min(values)),
            "max": float(np.max(values))
        }
    else:
        closure_stats = {
            "count": 0,
            "mean": 0.0,
            "median": 0.0,
            "variance": 0.0,
            "std_dev": 0.0,
            "q1": 0.0,
            "q3": 0.0,
            "min": 0.0,
            "max": 0.0
        }

    return {
        "total_records": len(records),
        "complaints": complaints,
        "agencies": agencies,
        "closure_stats": closure_stats,
        "daily_requests": daily_requests
    }


def export_counter(counter, filename, column_name):
    """Export ranking data to CSV."""
    path = OUTPUT_DIR / filename

    with open(path, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([column_name, "request_count"])

        for name, count in counter.most_common():
            writer.writerow([name, count])


def export_reports(results):
    """Export reports and closure time statistics."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    export_counter(
        results["complaints"],
        "complaint_type_counts.csv",
        "complaint_type"
    )

    export_counter(
        results["agencies"],
        "agency_counts.csv",
        "agency"
    )

    stats = results["closure_stats"]

    with open(
        OUTPUT_DIR / "closure_time.txt",
        "w",
        encoding="utf-8"
    ) as file:
        file.write("NYC 311 ANALYTICS REPORT\n")
        file.write("=" * 40 + "\n\n")

        file.write(f"Total records: {results['total_records']}\n")

        file.write("\nCLOSURE TIME (HOURS)\n")
        for key, value in stats.items():
            file.write(f"{key}: {value:.2f}\n")

    print(f"Reports exported to: {OUTPUT_DIR}")


def main():
    parser = argparse.ArgumentParser(
        description="NYC 311 Analytics"
    )

    parser.add_argument(
        "--complaint-type",
        help="Filter by complaint type"
    )

    parser.add_argument(
        "--agency",
        help="Filter by agency"
    )

    args = parser.parse_args()

    if not DATA_FILE.exists():
        print(f"Dataset not found: {DATA_FILE}")
        return

    records = load_data(DATA_FILE)

    records = filter_data(
        records,
        complaint_type=args.complaint_type,
        agency=args.agency
    )

    if not records:
        print("No records found for the selected filters.")
        return

    results = analyze_data(records)

    print("\nNYC 311 ANALYTICS")
    print("=" * 40)
    print("Total records:", results["total_records"])

    print("\nTOP 10 COMPLAINT TYPES:")
    for name, count in results["complaints"].most_common(10):
        print(f"{name}: {count}")

    print("\nTOP 10 AGENCIES:")
    for name, count in results["agencies"].most_common(10):
        print(f"{name}: {count}")

    print("\nCLOSURE TIME (HOURS):")
    for key, value in results["closure_stats"].items():
        print(f"{key}: {value:.2f}")

    export_reports(results)


if __name__ == "__main__":
    main()