from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from activitywatch import ActivityWatchClient, ActivitySegment

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
CONFIG_PATH = ROOT / "projects.json"


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def matches_domain(domain: str, candidates: list[str]) -> bool:
    domain = domain.lower().strip()
    return any(domain == c.lower() or domain.endswith("." + c.lower()) for c in candidates)


def classify(segment: ActivitySegment, project_name: str, rules: dict) -> ActivitySegment:
    domain = segment.domain.lower()
    app = segment.app.lower()
    title = segment.title.lower()

    if matches_domain(domain, rules.get("excluded_domains", [])) or any(x.lower() in app for x in rules.get("excluded_apps", [])):
        segment.classification = "EXCLUDED"
    elif matches_domain(domain, rules.get("approved_domains", [])):
        segment.classification = "APPROVED"
    elif any(x.lower() in app for x in rules.get("approved_apps", [])):
        segment.classification = "APPROVED"
    elif any(k.lower() in title for k in rules.get("title_keywords", [])):
        segment.classification = "APPROVED"
    elif matches_domain(domain, rules.get("review_domains", [])):
        segment.classification = "REVIEW"
    elif any(x.lower() in app for x in rules.get("review_apps", [])):
        segment.classification = "REVIEW"
    else:
        segment.classification = "REVIEW"

    segment.project = project_name
    return segment


def fmt(seconds: float) -> str:
    mins = int(round(seconds / 60))
    h, m = divmod(mins, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


def parse_date(value: str):
    """Accept DD/MM/YYYY (preferred) and legacy YYYY-MM-DD input."""
    for pattern in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            pass
    raise argparse.ArgumentTypeError("Date must be in DD/MM/YYYY format, e.g. 11/09/2026")


def write_reports(day, segments: list[ActivitySegment], project: str, tz: str) -> tuple[Path, Path]:
    REPORTS.mkdir(exist_ok=True)
    display_day = day.strftime("%d/%m/%Y")
    filename_day = day.strftime("%d-%m-%Y")  # '/' is not valid in Windows filenames
    txt_path = REPORTS / f"{filename_day}-summary.txt"
    csv_path = REPORTS / f"{filename_day}-detail.csv"

    totals = defaultdict(float)
    by_source = defaultdict(float)
    for s in segments:
        totals[s.classification] += s.duration_seconds
        source = s.domain or s.app or "Unknown"
        by_source[(s.classification, source)] += s.duration_seconds

    active = sum(s.duration_seconds for s in segments)
    lines = [
        f"DATE: {display_day}",
        f"TIMEZONE: {tz}",
        f"PROJECT RULESET: {project}",
        "",
        f"TOTAL ACTIVE CAPTURED: {fmt(active)}",
        f"APPROVED: {fmt(totals['APPROVED'])}",
        f"NEEDS REVIEW: {fmt(totals['REVIEW'])}",
        f"EXCLUDED: {fmt(totals['EXCLUDED'])}",
        "",
    ]

    for cls in ("APPROVED", "REVIEW", "EXCLUDED"):
        lines.append(cls)
        rows = sorted(((src, sec) for (c, src), sec in by_source.items() if c == cls), key=lambda x: x[1], reverse=True)
        if not rows:
            lines.append("  (none)")
        else:
            for src, sec in rows:
                lines.append(f"  {src:<35} {fmt(sec)}")
        lines.append("")

    lines.append("DETAIL")
    for s in sorted(segments, key=lambda x: x.start):
        start = datetime.fromisoformat(s.start).astimezone(ZoneInfo(tz)).strftime("%H:%M:%S")
        end = datetime.fromisoformat(s.end).astimezone(ZoneInfo(tz)).strftime("%H:%M:%S")
        source = s.domain or s.app
        lines.append(f"{start}-{end} | {s.classification:<8} | {fmt(s.duration_seconds):>7} | {source} | {s.title[:120]}")

    txt_path.write_text("\n".join(lines), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["start", "end", "duration_seconds", "app", "title", "url", "domain", "classification", "project"])
        writer.writeheader()
        for s in segments:
            row = s.to_dict()
            row.pop("afk", None)
            writer.writerow(row)

    return txt_path, csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an ActivityWatch-based daily work report.")
    parser.add_argument("--date", type=parse_date, help="Date in DD/MM/YYYY. Defaults to today.")
    parser.add_argument("--project", default="Parish Dashboard")
    parser.add_argument("--timezone", default="Asia/Kolkata")
    args = parser.parse_args()

    tz = ZoneInfo(args.timezone)
    day = args.date if args.date else datetime.now(tz).date()
    local_start = datetime.combine(day, datetime.min.time(), tzinfo=tz)
    local_end = local_start + timedelta(days=1)

    config = load_config()
    rules = config["projects"].get(args.project)
    if not rules:
        raise SystemExit(f"Project '{args.project}' not found in projects.json")

    client = ActivityWatchClient()
    if not client.healthcheck():
        raise SystemExit("ActivityWatch is not reachable at http://127.0.0.1:5600. Start ActivityWatch and try again.")

    segments = client.build_timeline(local_start, local_end)
    min_seconds = float(config.get("defaults", {}).get("minimum_segment_seconds", 3))
    segments = [classify(s, args.project, rules) for s in segments if s.duration_seconds >= min_seconds]

    txt_path, csv_path = write_reports(day, segments, args.project, args.timezone)
    print(f"Created: {txt_path}")
    print(f"Created: {csv_path}")


if __name__ == "__main__":
    main()
