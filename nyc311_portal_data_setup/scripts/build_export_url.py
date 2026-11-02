
import json
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "dataset_config.json"


def build_where_clause(filters: dict) -> str:
    start = filters["created_date_start_inclusive"]
    end = filters["created_date_end_exclusive"]
    clauses = [f"created_date >= '{start}'", f"created_date < '{end}'"]
    borough = filters.get("borough")
    if borough:
        clauses.append(f"borough = '{borough.upper()}'")
    return " AND ".join(clauses)


def build_url(config: dict) -> str:
    where = build_where_clause(config["filters"])
    query = (
        f"$where={quote(where, safe='')}"
        f"&$order={quote('created_date', safe='')}"
        f"&$limit={config['max_rows_requested']}"
    )
    return f"{config['api_base_url']}?{query}"


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    print("SoQL filter (copy into DATA_SOURCE.md):")
    print(f"  {build_where_clause(config['filters'])}\n")
    print("Export URL:")
    print(f"  {build_url(config)}\n")
    print(f"Save the downloaded file as: {config['csv_path']}")


if __name__ == "__main__":
    main()
