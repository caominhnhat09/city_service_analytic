import argparse
import csv
import os
import re
import sys
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional


# Paths are resolved from this file's location, so the script works from any
# working directory and on any OS.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARSER_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(PARSER_DIR)

DEFAULT_FILEPATH = os.path.join(PROJECT_ROOT, "portal_data_setup", "data", "nyc311_brooklyn_2026-07.csv")

# Output folder for cleaned data and quality report: parser/data
OUTPUT_DIR = os.path.join(PARSER_DIR, "data")

DATE_FORMATS = (
    '%Y-%m-%dT%H:%M:%S.%f',   # API export
    '%Y-%m-%dT%H:%M:%S',      # API export without fractional seconds
    '%m/%d/%Y %I:%M:%S %p',   # portal (web) export
)

OUTPUT_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'

# Status grouping. Anything that is not Closed and not missing counts as open
# (Open, In Progress, Assigned, Started, Pending, ...).
CLOSED_STATUSES = {'Closed'}
MISSING_STATUSES = {'', 'Unspecified'}

# Some portal exports use display names for these columns. Headers are normalized
# (lowercase, non-alphanumerics -> '_') and then mapped to the target names below
# (complaint_type, descriptor, descriptor_2), so either naming parses and exports the same way.
COLUMN_ALIASES = {
    'complaint_type': {'complaint_type', 'problem', 'problem_formerly_complaint_type'},
    'descriptor': {'descriptor', 'problem_detail', 'problem_detail_formerly_descriptor'},
    'descriptor_2': {'descriptor_2', 'additional_details'},
}
_ALIAS_LOOKUP = {alias: canonical for canonical, aliases in COLUMN_ALIASES.items() for alias in aliases}

DATE_COLUMNS = ('created_date', 'closed_date', 'due_date', 'resolution_action_updated_date')


def normalize_date_text(value: Optional[str]) -> str:
    """Rewrites a date string in the API style; returns it unchanged if it cannot be parsed."""
    if not value or not value.strip():
        return ''
    dt = ServiceRequest._parse_date(value)
    return format_date(dt) if dt else value


def format_date(dt: Optional[datetime]) -> str:
    """Writes a datetime in the API style, e.g. 2026-07-01T00:00:13.000."""
    return dt.strftime(OUTPUT_DATE_FORMAT)[:-3] if dt else ''


def normalize_header(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', name.strip().lower()).strip('_')


def canonical_column(name: str) -> str:
    """Maps a raw CSV header (old or new naming) to its canonical name."""
    norm = normalize_header(name)
    return _ALIAS_LOOKUP.get(norm, norm)


class ServiceRequest:
    """OOP representation of a single NYC 311 service request record."""
    def __init__(self, row: Dict[str, Optional[str]]):
        # Full raw row (canonical column names), kept so the export can include every column
        self.raw = row
        self.unique_key = (row.get('unique_key') or '').strip()
        self.agency = row.get('agency')
        self.complaint_type = row.get('complaint_type')
        self.borough = row.get('borough')
        self.status = (row.get('status') or '').strip()

        self.created_date_str = row.get('created_date')
        self.closed_date_str = row.get('closed_date')

        self.created_dt = self._parse_date(self.created_date_str)
        self.closed_dt = self._parse_date(self.closed_date_str)

        # Timestamp quality checks
        self.unparseable_date = bool(
            (self.created_dt is None and self.created_date_str) or
            (self.closed_dt is None and self.closed_date_str)
        )
        self.closed_before_created = bool(
            self.created_dt and self.closed_dt and self.closed_dt < self.created_dt
        )
        self.closed_without_date = self.status in CLOSED_STATUSES and not self.closed_date_str

        # Records with unusable timestamps are excluded from the clean export
        self.is_malformed_date = self.unparseable_date or self.closed_before_created

    @property
    def status_group(self) -> str:
        if self.status in MISSING_STATUSES:
            return 'missing'
        if self.status in CLOSED_STATUSES:
            return 'closed'
        return 'open'

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None


class RequestIndex:
    """Handles CSV I/O, dictionary indexing, and reporting."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.records: Dict[str, ServiceRequest] = {}
        # Canonical column names from the raw file, in their original order
        self.columns: List[str] = []

        # Quality report trackers
        self.duplicates: List[str] = []
        self.missing_id_rows = 0
        self.unparseable_dates: List[str] = []
        self.closed_before_created: List[str] = []
        self.closed_without_date: List[str] = []

    def load_and_index(self):
        """Reads the CSV file, indexes unique records, and logs quality issues."""
        with open(self.filepath, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            # Rename headers once: "Problem (formerly Complaint Type)" -> complaint_type, etc.
            reader.fieldnames = [canonical_column(h) for h in (reader.fieldnames or [])]
            # Valid columns: non-blank headers, first occurrence of each name
            self.columns = list(dict.fromkeys(h for h in reader.fieldnames if h))
            for row in reader:
                record = ServiceRequest(row)

                if not record.unique_key:
                    self.missing_id_rows += 1
                    continue

                # Duplicates are logged and skipped, so they are not double-counted
                if record.unique_key in self.records:
                    self.duplicates.append(record.unique_key)
                    continue
                self.records[record.unique_key] = record

                if record.unparseable_date:
                    self.unparseable_dates.append(record.unique_key)
                if record.closed_before_created:
                    self.closed_before_created.append(record.unique_key)
                if record.closed_without_date:
                    self.closed_without_date.append(record.unique_key)

    @staticmethod
    def status_summary(records: List[ServiceRequest]) -> Dict[str, Counter]:
        """Counts records per status group and per raw status value."""
        groups = Counter(r.status_group for r in records)
        raw = Counter(r.status or '(empty)' for r in records)
        return {'groups': groups, 'raw': raw}

    def filter_records(self, agency: Optional[str] = None, problem_type: Optional[str] = None,
                       status: Optional[str] = None) -> List[ServiceRequest]:
        """Returns records matching all given filters (case-insensitive)."""
        def matches(value: Optional[str], wanted: Optional[str]) -> bool:
            return wanted is None or (value or '').lower() == wanted.lower()

        return [
            r for r in self.records.values()
            if matches(r.agency, agency)
            and matches(r.complaint_type, problem_type)
            and matches(r.status, status)
        ]

    def unique_values(self, attr_name: str) -> List[str]:
        return sorted({getattr(r, attr_name) for r in self.records.values() if getattr(r, attr_name)})

    def export_clean_csv(self, records_to_export: List[ServiceRequest], output_filename: str):
        """Exports filtered and cleaned records to a new CSV file."""
        # Drop records with malformed timestamps (duplicates are already removed by the dict index)
        clean_records = [r for r in records_to_export if not r.is_malformed_date]

        if not clean_records:
            print("No clean records to export.")
            return

        # Every valid column from the raw file, exported under its target snake_case name
        # (portal display names like "Problem (formerly Complaint Type)" become complaint_type)
        with open(output_filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.columns, extrasaction='ignore')
            writer.writeheader()
            for r in clean_records:
                row = {col: r.raw.get(col) for col in self.columns}
                # Use the whitespace-trimmed values the parser validated
                row['unique_key'] = r.unique_key
                row['status'] = r.status
                for col in DATE_COLUMNS:
                    if col in row:
                        row[col] = normalize_date_text(row[col])
                writer.writerow(row)
        excluded = len(records_to_export) - len(clean_records)
        print(f"[+] Exported {len(clean_records):,} clean records "
              f"({excluded:,} excluded for malformed timestamps) to: {output_filename}")

    def report_lines(self, selected: List[ServiceRequest], filter_desc: Optional[str]) -> List[str]:
        """Builds the summary/quality report shared by the console and the text file."""
        overall = self.status_summary(list(self.records.values()))
        lines = [
            "=== DATA QUALITY REPORT ===",
            f"Source file                 : {self.filepath}",
            f"Total unique records parsed : {len(self.records):,}",
            f"Rows missing unique_key     : {self.missing_id_rows:,}",
            f"Duplicate IDs found         : {len(self.duplicates):,}",
            f"Unparseable timestamps      : {len(self.unparseable_dates):,}",
            f"Closed before created       : {len(self.closed_before_created):,}",
            f"Closed without closed_date  : {len(self.closed_without_date):,}",
            "",
            "=== STATUS REPORT (all records) ===",
            *self._status_lines(overall),
        ]

        if filter_desc:
            filtered = self.status_summary(selected)
            lines += [
                "",
                "=== FILTER RESULTS ===",
                f"Filter applied              : {filter_desc}",
                f"Records matching filter     : {len(selected):,}",
                *self._status_lines(filtered),
            ]
        return lines

    @staticmethod
    def _status_lines(summary: Dict[str, Counter]) -> List[str]:
        groups, raw = summary['groups'], summary['raw']
        lines = [
            f"Open records                : {groups['open']:,}",
            f"Closed records              : {groups['closed']:,}",
            f"Missing-status records      : {groups['missing']:,}",
            "  Breakdown by raw status:",
        ]
        lines += [f"    {status:<24}: {count:,}" for status, count in raw.most_common()]
        return lines

    def generate_quality_report(self, output_filename: str, selected: List[ServiceRequest],
                                filter_desc: Optional[str]):
        """Writes the summary/quality report plus the full lists of faulty IDs."""
        issue_lists = [
            ("DUPLICATE IDs", self.duplicates),
            ("UNPARSEABLE TIMESTAMP IDs", self.unparseable_dates),
            ("CLOSED-BEFORE-CREATED IDs", self.closed_before_created),
            ("CLOSED-WITHOUT-CLOSED_DATE IDs", self.closed_without_date),
        ]
        with open(output_filename, mode='w', encoding='utf-8') as f:
            f.write("\n".join(self.report_lines(selected, filter_desc)) + "\n")
            for title, ids in issue_lists:
                if ids:
                    f.write(f"\n--- {title} ({len(ids):,}) ---\n")
                    f.write("\n".join(ids) + "\n")
        print(f"[+] Quality report saved to: {output_filename}")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Parse, clean and filter NYC 311 service requests.")
    p.add_argument('--input', default=DEFAULT_FILEPATH, help="Path to the raw 311 CSV file")
    p.add_argument('--agency', help="Filter by agency, e.g. DSNY")
    p.add_argument('--problem-type', help='Filter by complaint type, e.g. "Abandoned Bike"')
    p.add_argument('--status', help="Filter by raw status value, e.g. Closed")
    p.add_argument('--list', choices=['agency', 'problem-type', 'status'],
                   help="Print available values for a column and exit")
    p.add_argument('--interactive', action='store_true',
                   help="Choose a filter from a menu instead of using flags")
    return p


def interactive_filter(index: RequestIndex) -> Dict[str, str]:
    """Menu-driven fallback for choosing a single filter."""
    # lstrip BOM: PowerShell prepends one when piping input
    wants_filter = input("\nDo you want to apply a filter? (y/n): ").lstrip('﻿').strip().lower()
    if wants_filter != 'y':
        return {}

    attr_map = {
        '1': ('complaint_type', 'problem_type', 'Problem / Complaint Type'),
        '2': ('agency', 'agency', 'Agency'),
        '3': ('status', 'status', 'Status'),
    }
    print("\nSelect a column to filter by:")
    print("1. problem (complaint_type)")
    print("2. agency")
    print("3. status")
    col_choice = input("Enter choice (1-3): ").strip()
    if col_choice not in attr_map:
        print("Invalid column choice. Proceeding without filters.")
        return {}

    attr_name, key, display_name = attr_map[col_choice]
    values = index.unique_values(attr_name)
    print(f"\nAvailable {display_name}s:")
    for i, val in enumerate(values, 1):
        print(f"{i}. {val}")

    try:
        val_idx = int(input(f"Enter choice (1-{len(values)}): ").strip()) - 1
    except ValueError:
        print("Invalid input format. Proceeding without filters.")
        return {}
    if not 0 <= val_idx < len(values):
        print("Invalid selection. Proceeding without filters.")
        return {}
    return {key: values[val_idx]}


def main():
    args = build_arg_parser().parse_args()

    print(f"Loading data from {args.input}...")
    index = RequestIndex(args.input)
    try:
        index.load_and_index()
    except FileNotFoundError:
        print(f"Error: Could not find the file at {args.input}.")
        sys.exit(1)

    list_attrs = {'agency': 'agency', 'problem-type': 'complaint_type', 'status': 'status'}
    if args.list:
        for val in index.unique_values(list_attrs[args.list]):
            print(val)
        return

    filters = {k: v for k, v in
               {'agency': args.agency, 'problem_type': args.problem_type, 'status': args.status}.items() if v}
    if args.interactive:
        filters = interactive_filter(index)

    if filters:
        selected = index.filter_records(**filters)
        filter_desc = ", ".join(f"{k} = '{v}'" for k, v in filters.items())
        if not selected:
            print(f"Warning: no records match {filter_desc}. Use --list to see valid values.")
    else:
        selected = list(index.records.values())
        filter_desc = None

    print()
    print("\n".join(index.report_lines(selected, filter_desc)))

    print("\n--- EXPORTING FILES ---")
    csv_filename = "cleaned_data.csv"
    if filters:
        safe_name = "_".join(f"{k}_{v}" for k, v in filters.items())
        safe_name = "".join(c if c.isalnum() else "_" for c in safe_name.lower()).strip("_")
        csv_filename = f"cleaned_data_{safe_name}.csv"

    # Replace previous outputs: remove old cleaned CSVs before writing the new one
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for old_file in os.listdir(OUTPUT_DIR):
        if old_file.startswith("cleaned_data") and old_file.endswith(".csv"):
            os.remove(os.path.join(OUTPUT_DIR, old_file))

    index.export_clean_csv(selected, os.path.join(OUTPUT_DIR, csv_filename))
    index.generate_quality_report(os.path.join(OUTPUT_DIR, "quality_report.txt"), selected, filter_desc)


if __name__ == "__main__":
    main()