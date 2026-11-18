import csv
from pathlib import Path
from datetime import datetime
from collections import Counter

import numpy as np
import matplotlib.pyplot as plt


PROJECT_DIR = Path(__file__).resolve().parent.parent

DATA_FILE = PROJECT_DIR / "parser" / "data" / "cleaned_data.csv"

OUTPUT_DIR = PROJECT_DIR / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_date(value):
    """Convert an ISO timestamp string into a datetime object."""
    if not value or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip())
    except ValueError:
        return None


def load_data():
    with open(DATA_FILE, encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def plot_complaints(records):
    counts = Counter(
        row["complaint_type"]
        for row in records
        if row["complaint_type"]
    )

    top = counts.most_common(10)

    labels = [item[0] for item in top]
    values = [item[1] for item in top]

    plt.figure(figsize=(12, 6))
    plt.bar(labels, values)

    plt.title("Top 10 Complaint Types")
    plt.xlabel("Complaint Type")
    plt.ylabel("Number of Requests")

    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    plt.savefig(OUTPUT_DIR / "complaint_types.png")
    plt.close()


def plot_agencies(records):
    counts = Counter(
        row["agency"]
        for row in records
        if row["agency"]
    )

    top = counts.most_common(10)

    labels = [item[0] for item in top]
    values = [item[1] for item in top]

    plt.figure(figsize=(10, 6))
    plt.barh(labels, values)

    plt.title("Top 10 Agencies")
    plt.xlabel("Number of Requests")
    plt.ylabel("Agency")

    plt.tight_layout()

    plt.savefig(OUTPUT_DIR / "agencies.png")
    plt.close()


def plot_daily_requests(records):
    counts = Counter()

    for row in records:
        date = row["created_date"]

        if date:
            day = date[:10]
            counts[day] += 1

    dates = sorted(counts.keys())
    values = [counts[date] for date in dates]

    plt.figure(figsize=(12, 6))

    plt.plot(dates, values, marker="o")

    plt.title("Daily Requests")
    plt.xlabel("Date")
    plt.ylabel("Number of Requests")

    plt.xticks(rotation=45)

    plt.tight_layout()

    plt.savefig(OUTPUT_DIR / "daily_requests.png")
    plt.close()


def _draw_dual_bar_subplot(ax1, categories, counts, means, medians, title, left_color, right_color):
    """Helper function to draw a dual-axis grouped bar chart with annotations."""
    x = np.arange(len(categories))
    width = 0.35

    # Left axis: Number of Requests
    bars1 = ax1.bar(
        x - width / 2,
        counts,
        width,
        color=left_color,
        label="Number of Requests"
    )
    ax1.set_ylabel("Number of Requests", color=left_color, fontweight="bold")
    ax1.tick_params(axis="y", labelcolor=left_color)
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories)
    ax1.set_ylim(0, max(counts) * 1.22 if max(counts) > 0 else 10)
    ax1.grid(axis="y", linestyle="--", alpha=0.4)

    # Right axis: Mean Closure Time (Hours)
    ax2 = ax1.twinx()
    bars2 = ax2.bar(
        x + width / 2,
        means,
        width,
        color=right_color,
        label="Mean Closure Time (Hours)"
    )
    ax2.set_ylabel("Mean Closure Time (Hours)", color=right_color, fontweight="bold")
    ax2.tick_params(axis="y", labelcolor=right_color)
    ax2.set_ylim(0, max(means) * 1.22 if max(means) > 0 else 10)

    ax1.set_title(title, pad=12, fontweight="bold")

    # Annotate Request Counts
    for bar in bars1:
        height = bar.get_height()
        ax1.annotate(
            f"{int(height):,}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            color=left_color,
            fontsize=9,
            fontweight="bold"
        )

    # Annotate Mean and Median Closure Times
    for bar, med in zip(bars2, medians):
        height = bar.get_height()
        ax2.annotate(
            f"{height:.2f}h\n(Med: {med:.2f}h)",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            color=right_color,
            fontsize=8.5,
            fontweight="bold"
        )

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=8.5)


def plot_comparison(records):
    """Compare request counts, mean, and median closure times across agencies and July periods."""
    agency_data = {
        "NYPD": {"count": 0, "durations": []},
        "HPD": {"count": 0, "durations": []}
    }

    period_data = {
        "First Half": {"count": 0, "durations": []},
        "Second Half": {"count": 0, "durations": []}
    }

    for row in records:
        agency = row.get("agency", "").strip().upper()
        created = parse_date(row.get("created_date", ""))
        closed = parse_date(row.get("closed_date", ""))

        duration = None
        if created and closed:
            diff = (closed - created).total_seconds() / 3600
            if diff >= 0:
                duration = diff

        # Group by NYPD vs HPD
        if agency in agency_data:
            agency_data[agency]["count"] += 1
            if duration is not None:
                agency_data[agency]["durations"].append(duration)

        # Group by First Half vs Second Half of July
        if created and created.month == 7:
            period_key = "First Half" if created.day <= 15 else "Second Half"
            period_data[period_key]["count"] += 1
            if duration is not None:
                period_data[period_key]["durations"].append(duration)

    def get_metrics(bucket):
        count = bucket["count"]
        durs = bucket["durations"]
        mean_val = float(np.mean(durs)) if durs else 0.0
        med_val = float(np.median(durs)) if durs else 0.0
        return count, mean_val, med_val

    # Prepare data for Chart 1 (Agencies)
    nypd_c, nypd_mean, nypd_med = get_metrics(agency_data["NYPD"])
    hpd_c, hpd_mean, hpd_med = get_metrics(agency_data["HPD"])

    agency_labels = ["NYPD\n(Police Department)", "HPD\n(Housing Preservation & Dev.)"]
    agency_counts = [nypd_c, hpd_c]
    agency_means = [nypd_mean, hpd_mean]
    agency_medians = [nypd_med, hpd_med]

    # Prepare data for Chart 2 (July Time Periods)
    p1_c, p1_mean, p1_med = get_metrics(period_data["First Half"])
    p2_c, p2_mean, p2_med = get_metrics(period_data["Second Half"])

    period_labels = ["First Half of July\n(July 1 – July 15)", "Second Half of July\n(July 16 – July 31)"]
    period_counts = [p1_c, p2_c]
    period_means = [p1_mean, p2_mean]
    period_medians = [p1_med, p2_med]

    # Create side-by-side subplots
    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(15, 6.5))

    _draw_dual_bar_subplot(
        ax_left,
        agency_labels,
        agency_counts,
        agency_means,
        agency_medians,
        title="Chart 1: NYPD vs. HPD Comparison\n(Request Count & Closure Time)",
        left_color="#3472B0",
        right_color="#D96B27"
    )

    _draw_dual_bar_subplot(
        ax_right,
        period_labels,
        period_counts,
        period_means,
        period_medians,
        title="Chart 2: July Time Period Comparison\n(Request Count & Closure Time)",
        left_color="#3E8E5E",
        right_color="#7E57C2"
    )

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "compare.png", dpi=150)
    plt.close()


def main():
    records = load_data()

    plot_complaints(records)
    plot_agencies(records)
    plot_daily_requests(records)
    plot_comparison(records)

    print("4 charts created successfully!")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()