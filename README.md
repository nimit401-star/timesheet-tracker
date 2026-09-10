# Timesheet Tracker V2

Local, privacy-first daily time-reporting companion for ActivityWatch.

## What it does

- Uses ActivityWatch's existing always-on foreground activity and AFK tracking.
- Reads app/window activity plus browser URL/title data when available.
- Removes AFK overlap from captured foreground activity.
- Classifies activity using project rules in `projects.json`.
- Generates a concise daily `.txt` summary for review or sharing with ChatGPT.
- Generates a detailed `.csv` audit file for troubleshooting and manual review.
- No cloud server, paid API, or remote browsing-history storage is required.

## Prerequisites

1. Windows with Python 3.10+ installed.
2. ActivityWatch installed and running.
3. ActivityWatch browser watcher installed if URL/domain reporting is desired.

ActivityWatch should be reachable locally at:

`http://127.0.0.1:5600`

## First-time setup

1. Clone or download this repository.
2. Double-click `Setup.bat`.
3. Confirm ActivityWatch is running.
4. Double-click `Generate Today Report.bat`.

Alternatively:

```powershell
python -m pip install -r requirements.txt
python daily_report.py
```

## Output

Reports are written locally to the `reports/` folder:

- `YYYY-MM-DD-summary.txt`
- `YYYY-MM-DD-detail.csv`

The summary includes:

- total active captured time
- approved time
- needs-review time
- excluded time
- duration by app/domain
- a chronological detail list with window titles

## Generate another date

```powershell
python daily_report.py --date 2026-09-11
```

or run:

```powershell
python app.py
```

and choose the date interactively.

## Project rules

Edit `projects.json` to tune classification. Each project can define:

- `approved_domains`
- `review_domains`
- `excluded_domains`
- `approved_apps`
- `review_apps`
- `excluded_apps`
- `title_keywords`

The initial rules are intentionally conservative. ChatGPT, Google, WhatsApp, Outlook, Teams and YouTube generally stay in `REVIEW` because they may be work-related or personal depending on context.

## Privacy

The script talks only to the local ActivityWatch API on `127.0.0.1`. Report files remain on the PC unless you choose to share them.

Raw ActivityWatch browsing history is not uploaded by this project.

## Recommended daily workflow

1. Leave ActivityWatch running during the workday.
2. At the end of the day, run `Generate Today Report.bat`.
3. Review `reports/YYYY-MM-DD-summary.txt`.
4. Share the summary with ChatGPT together with calendar meetings.
5. Use the generated analysis to prepare the final timesheet entry.

## Current limitation

The V2 classifier is rule-based. Supporting tools such as ChatGPT or WhatsApp are not automatically treated as billable work. They remain review items so the final timesheet stays defensible.
