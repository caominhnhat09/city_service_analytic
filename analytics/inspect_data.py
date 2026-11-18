
import csv
from pathlib import Path

# Project root directory
PROJECT_DIR = Path(__file__).resolve().parent.parent

def inspect_csv_files():
    csv_files = list(PROJECT_DIR.rglob("*.csv"))

    if not csv_files:
        print("No CSV files found!")
        return

    print(f"Found {len(csv_files)} CSV file(s).\n")

    for file_path in csv_files:
        print("=" * 60)
        print(f"FILE: {file_path.relative_to(PROJECT_DIR)}")

        try:
            with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file)

                print("\nCOLUMNS:")
                print(reader.fieldnames)

                print("\nFIRST 5 RECORDS:")
                for i, row in enumerate(reader):
                    if i >= 5:
                        break
                    print(row)

        except UnicodeDecodeError:
            print("Cannot read with UTF-8 encoding.")
        except Exception as error:
            print(f"Error: {error}")

if __name__ == "__main__":
    inspect_csv_files()
