import csv
import argparse
from datetime import datetime
from typing import Dict, List

# Default path for running directly from the IDE
DEFAULT_FILEPATH = "portal_data_setup\\data\\nyc311_brooklyn_2026-07.csv"

class ServiceRequest:
    """OOP representation of a single NYC 311 service request record."""
    def __init__(self, row: dict):
        self.unique_key = row.get('unique_key')
        self.agency = row.get('agency')
        self.complaint_type = row.get('complaint_type')
        self.borough = row.get('borough')
        self.status = row.get('status')
        
        self.created_date_str = row.get('created_date')
        self.closed_date_str = row.get('closed_date')

        self.created_dt = self._parse_date(self.created_date_str)
        self.closed_dt = self._parse_date(self.closed_date_str)
        
        # Identify malformed timestamps[cite: 2]
        self.is_malformed_date = (self.created_dt is None and self.created_date_str) or \
                                 (self.closed_dt is None and self.closed_date_str)

    def _parse_date(self, date_str: str):
        if not date_str:
            return None
        try:
            # Matches the ISO 8601 format identified in your dataset[cite: 1]
            return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError:
            return None

class RequestIndex:
    """Handles CSV I/O, dictionary indexing, and reporting."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.records: Dict[str, ServiceRequest] = {}
        
        # Quality report trackers[cite: 2]
        self.duplicates: List[str] = []
        self.malformed_records: List[str] = []
        
        # Status report trackers[cite: 2]
        self.open_count = 0
        self.closed_count = 0
        self.missing_status_count = 0

    def load_and_index(self):
        """Reads the CSV file, indexes records, and logs statuses and quality issues."""
        with open(self.filepath, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                record = ServiceRequest(row)
                
                if not record.unique_key:
                    continue
                    
                # Identify duplicate IDs[cite: 2]
                if record.unique_key in self.records:
                    self.duplicates.append(record.unique_key)
                else:
                    self.records[record.unique_key] = record
                
                # Identify malformed timestamps[cite: 2]
                if record.is_malformed_date:
                    self.malformed_records.append(record.unique_key)

                # Report open, closed and missing-status records separately[cite: 2]
                if record.status == 'Open':
                    self.open_count += 1
                elif record.status == 'Closed':
                    self.closed_count += 1
                else:
                    self.missing_status_count += 1

    def filter_records(self, agency: str = None, problem_type: str = None) -> List[ServiceRequest]:
        """Filtering logic for CLI support[cite: 2]."""
        filtered = []
        for record in self.records.values():
            if agency and record.agency != agency:
                continue
            if problem_type and record.complaint_type != problem_type:
                continue
            filtered.append(record)
        return filtered

def main():
    """Main execution block integrating the interactive CLI filter."""
    print(f"Loading data from {DEFAULT_FILEPATH}...")
    index = RequestIndex(DEFAULT_FILEPATH)
    
    try:
        index.load_and_index()
    except FileNotFoundError:
        print(f"Error: Could not find the file at {DEFAULT_FILEPATH}.")
        return

    filtered_results = None
    applied_filter_name = None

    # Interactive filtering prompt to support configurable problem type or agency
    wants_filter = input("\nDo you want to apply a filter? (y/n): ").strip().lower()
    
    if wants_filter == 'y':
        print("\nSelect a column to filter by:")
        print("1. problem (complaint_type)")
        print("2. agency")
        print("3. status")
        
        col_choice = input("Enter choice (1-3): ").strip()
        
        # Map user choice to the corresponding object attribute
        attr_map = {
            '1': ('complaint_type', 'Problem / Complaint Type'),
            '2': ('agency', 'Agency'),
            '3': ('status', 'Status')
        }
        
        if col_choice in attr_map:
            attr_name, display_name = attr_map[col_choice]
            
            # Extract unique, non-empty values for the selected column
            unique_values = sorted(list(set(
                getattr(r, attr_name) for r in index.records.values() if getattr(r, attr_name)
            )))
            
            print(f"\nAvailable {display_name}s:")
            for i, val in enumerate(unique_values, 1):
                print(f"{i}. {val}")
                
            val_choice = input(f"Enter choice (1-{len(unique_values)}): ").strip()
            
            try:
                val_idx = int(val_choice) - 1
                if 0 <= val_idx < len(unique_values):
                    selected_val = unique_values[val_idx]
                    applied_filter_name = f"{display_name} = '{selected_val}'"
                    
                    # Apply the filter
                    filtered_results = [
                        r for r in index.records.values() 
                        if getattr(r, attr_name) == selected_val
                    ]
                else:
                    print("Invalid selection. Proceeding without filters.")
            except ValueError:
                print("Invalid input format. Proceeding without filters.")
        else:
            print("Invalid column choice. Proceeding without filters.")

    # Output Reports
    print("\n--- STATUS REPORT ---")
    print(f"Open records          : {index.open_count:,}")
    print(f"Closed records        : {index.closed_count:,}")
    print(f"Missing-status records: {index.missing_status_count:,}")
    
    print("\n--- QUALITY REPORT ---")
    print(f"Total unique records parsed : {len(index.records):,}")
    print(f"Duplicate IDs found         : {len(index.duplicates):,}")
    print(f"Malformed timestamps found  : {len(index.malformed_records):,}")
    
    if filtered_results is not None:
        print(f"\n--- FILTER RESULTS ---")
        print(f"Filter applied              : {applied_filter_name}")
        print(f"Records matching filter     : {len(filtered_results):,}")

if __name__ == "__main__":
    main()