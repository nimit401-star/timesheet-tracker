from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
import requests


DEFAULT_BASE_URL = "http://127.0.0.1:5600/api/0"


@dataclass
class ActivitySegment:
    start: str
    end: str
    duration_seconds: float
    app: str
    title: str
    url: str = ""
    domain: str = ""
    afk: bool = False
    classification: str = "REVIEW"
    project: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _event_bounds(event: dict[str, Any]) -> tuple[datetime, datetime]:
    start = _parse_dt(event["timestamp"])
    end = start + __import__("datetime").timedelta(seconds=float(event.get("duration", 0)))
    return start, end


def overlap_seconds(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> float:
    return max(0.0, (min(a_end, b_end) - max(a_start, b_start)).total_seconds())


def domain_from_url(url: str) -> str:
    if not url:
        return ""
    try:
        host = (urlparse(url).hostname or "").lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


class ActivityWatchClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def healthcheck(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/buckets", timeout=self.timeout)
            return response.ok
        except requests.RequestException:
            return False

    def get_buckets(self) -> dict[str, Any]:
        response = requests.get(f"{self.base_url}/buckets", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_events(self, bucket_id: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
        params = {"start": _iso(start), "end": _iso(end)}
        response = requests.get(
            f"{self.base_url}/buckets/{bucket_id}/events",
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def discover_buckets(self) -> tuple[str | None, str | None, list[str]]:
        buckets = self.get_buckets()
        window_bucket = None
        afk_bucket = None
        web_buckets: list[str] = []
        for bucket_id in buckets:
            lowered = bucket_id.lower()
            if "aw-watcher-window" in lowered:
                window_bucket = bucket_id
            elif "aw-watcher-afk" in lowered:
                afk_bucket = bucket_id
            elif "aw-watcher-web" in lowered:
                web_buckets.append(bucket_id)
        return window_bucket, afk_bucket, web_buckets

    def build_timeline(self, start: datetime, end: datetime) -> list[ActivitySegment]:
        window_bucket, afk_bucket, web_buckets = self.discover_buckets()
        if not window_bucket:
            raise RuntimeError("No ActivityWatch window bucket found. Make sure ActivityWatch is running.")

        window_events = self.get_events(window_bucket, start, end)
        afk_events = self.get_events(afk_bucket, start, end) if afk_bucket else []
        web_events: list[dict[str, Any]] = []
        for bucket_id in web_buckets:
            web_events.extend(self.get_events(bucket_id, start, end))

        web_ranges = [(*_event_bounds(e), e) for e in web_events]
        afk_ranges = [(*_event_bounds(e), e) for e in afk_events if str(e.get("data", {}).get("status", "")).lower() == "afk"]

        segments: list[ActivitySegment] = []
        for event in window_events:
            e_start, e_end = _event_bounds(event)
            if e_end <= start or e_start >= end:
                continue
            seg_start = max(e_start, start)
            seg_end = min(e_end, end)
            duration = max(0.0, (seg_end - seg_start).total_seconds())
            if duration <= 0:
                continue

            data = event.get("data", {})
            app = str(data.get("app", ""))
            title = str(data.get("title", ""))

            best_web = None
            best_overlap = 0.0
            if any(token in app.lower() for token in ("chrome", "edge", "firefox", "brave", "opera")):
                for w_start, w_end, w_event in web_ranges:
                    ov = overlap_seconds(seg_start, seg_end, w_start, w_end)
                    if ov > best_overlap:
                        best_overlap = ov
                        best_web = w_event

            url = ""
            if best_web:
                web_data = best_web.get("data", {})
                url = str(web_data.get("url", ""))
                title = str(web_data.get("title", title)) or title

            afk_seconds = sum(overlap_seconds(seg_start, seg_end, a_start, a_end) for a_start, a_end, _ in afk_ranges)
            active_seconds = max(0.0, duration - min(duration, afk_seconds))
            if active_seconds <= 0:
                continue

            segments.append(
                ActivitySegment(
                    start=seg_start.isoformat(),
                    end=seg_end.isoformat(),
                    duration_seconds=active_seconds,
                    app=app,
                    title=title,
                    url=url,
                    domain=domain_from_url(url),
                    afk=False,
                )
            )
        return segments
