from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from activitywatch import ActivityWatchClient

ROOT = Path(__file__).resolve().parent


def main() -> None:
    print("Timesheet Tracker V2")
    print("--------------------")

    client = ActivityWatchClient()
    if client.healthcheck():
        print("ActivityWatch: CONNECTED")
    else:
        print("ActivityWatch: NOT REACHABLE")
        print("Start ActivityWatch, then run this again.")
        raise SystemExit(1)

    print("\n1. Generate today's report")
    print("2. Generate report for another date")
    print("3. Exit")
    choice = input("\nChoose an option: ").strip()

    if choice == "1":
        cmd = [sys.executable, str(ROOT / "daily_report.py")]
    elif choice == "2":
        day = input("Enter date (YYYY-MM-DD): ").strip()
        cmd = [sys.executable, str(ROOT / "daily_report.py"), "--date", day]
    else:
        return

    result = subprocess.run(cmd, cwd=ROOT)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
