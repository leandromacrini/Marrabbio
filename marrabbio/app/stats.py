from __future__ import annotations

from collections import Counter, deque
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(ts: datetime) -> str:
    return ts.isoformat(timespec="seconds")


class StatsRecorder:
    def __init__(self, stats_dir: Path) -> None:
        stats_dir.mkdir(parents=True, exist_ok=True)
        now = _utc_now()
        self._startup_day = now.strftime("%Y-%m-%d")
        self._session_id = now.strftime("%Y-%m-%d_%H-%M-%S")
        self._file_path = stats_dir / f"stats_{self._session_id}.txt"
        self._fh = self._file_path.open("a", encoding="utf-8")
        self._lock = threading.Lock()
        self._counts: Counter[str] = Counter()
        self._recent_events: deque[dict[str, Any]] = deque(maxlen=40)
        self._write("session_started")

    def record_song_started(self, code: str, found: bool, title: str = "") -> None:
        self._write("song_started", code=code, found=found, title=title)

    def record_error(self, error: str, details: str = "") -> None:
        self._write("error", error=error, details=details)

    def _write(self, event: str, **data: Any) -> None:
        entry = {"ts": _iso(_utc_now()), "event": event, "data": data}
        with self._lock:
            self._apply(entry)
            self._recent_events.append(entry)
            # One line per log entry.
            self._fh.write(json.dumps(entry, ensure_ascii=True, separators=(",", ":")) + "\n")
            self._fh.flush()
            os.fsync(self._fh.fileno())

    def _apply(self, entry: dict[str, Any]) -> None:
        event = entry.get("event")
        data = entry.get("data", {})
        self._counts["events_total"] += 1
        if event == "song_started":
            self._counts["song_started_total"] += 1
            if data.get("found"):
                self._counts["song_found_total"] += 1
            else:
                self._counts["song_fallback_total"] += 1
        elif event == "error":
            self._counts["error_total"] += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "session_id": self._session_id,
                "startup_day": self._startup_day,
                "stats_file": str(self._file_path),
                "counters": dict(self._counts),
                "recent_events": list(self._recent_events),
            }

    def close(self) -> None:
        with self._lock:
            entry = {"ts": _iso(_utc_now()), "event": "session_stopped", "data": {}}
            self._fh.write(json.dumps(entry, ensure_ascii=True, separators=(",", ":")) + "\n")
            self._fh.flush()
            os.fsync(self._fh.fileno())
            self._fh.close()


def _parse_stats_file(path: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    counts["corrupted_lines"] += 1
                    continue

                event = entry.get("event")
                data = entry.get("data", {})
                counts["events_total"] += 1
                if event == "song_started":
                    counts["song_started_total"] += 1
                    if data.get("found"):
                        counts["song_found_total"] += 1
                    else:
                        counts["song_fallback_total"] += 1
                elif event == "error":
                    counts["error_total"] += 1
    except OSError:
        counts["file_read_errors"] += 1
    return counts


def _parse_ts_to_day(ts: str) -> str | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def _files_for_month(stats_dir: Path, year: int, month: int) -> list[Path]:
    # Include current and previous month files so sessions spanning month boundary
    # are still visible when aggregating by event timestamp day.
    ym = {(year, month)}
    if month == 1:
        ym.add((year - 1, 12))
    else:
        ym.add((year, month - 1))

    prefixes = [f"stats_{y:04d}-{m:02d}-" for y, m in ym]
    files = []
    for p in list_session_files(stats_dir):
        name = p.name
        if any(name.startswith(pref) for pref in prefixes):
            files.append(p)
    return files


def _song_counter_from_files(files: list[Path]) -> Counter[tuple[str, str]]:
    songs: Counter[tuple[str, str]] = Counter()
    for path in files:
        try:
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if entry.get("event") != "song_started":
                        continue
                    code = str(entry.get("data", {}).get("code", "")).strip()
                    title = str(entry.get("data", {}).get("title", "")).strip()
                    if code:
                        songs[(code, title)] += 1
        except OSError:
            continue
    return songs


def top_songs_all_time(stats_dir: Path, limit: int = 10) -> list[dict[str, Any]]:
    counts = _song_counter_from_files(list_session_files(stats_dir))
    return [
        {"code": code, "title": title, "count": count}
        for (code, title), count in counts.most_common(limit)
    ]


def top_songs_for_day(stats_dir: Path, day: str, limit: int = 10) -> list[dict[str, Any]]:
    try:
        y, m, _d = [int(x) for x in day.split("-")]
    except ValueError:
        return []

    counts: Counter[tuple[str, str]] = Counter()
    files = _files_for_month(stats_dir, y, m)
    for path in files:
        try:
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if entry.get("event") != "song_started":
                        continue
                    if _parse_ts_to_day(str(entry.get("ts", ""))) != day:
                        continue
                    data = entry.get("data", {})
                    code = str(data.get("code", "")).strip()
                    title = str(data.get("title", "")).strip()
                    if code:
                        counts[(code, title)] += 1
        except OSError:
            continue

    return [
        {"code": code, "title": title, "count": count}
        for (code, title), count in counts.most_common(limit)
    ]


def list_session_files(stats_dir: Path) -> list[Path]:
    if not stats_dir.exists():
        return []
    return sorted(stats_dir.glob("stats_*.txt"))


def list_calendar(stats_dir: Path) -> list[dict[str, Any]]:
    now = _utc_now()
    return list_calendar_for_month(stats_dir, now.year, now.month)


def list_calendar_for_month(stats_dir: Path, year: int, month: int) -> list[dict[str, Any]]:
    days: dict[str, Counter[str]] = {}
    files_per_day: dict[str, set[str]] = {}
    files = _files_for_month(stats_dir, year, month)

    for path in files:
        try:
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    day = _parse_ts_to_day(str(entry.get("ts", "")))
                    if not day:
                        continue
                    if not day.startswith(f"{year:04d}-{month:02d}-"):
                        continue
                    counts = days.setdefault(day, Counter())
                    files_set = files_per_day.setdefault(day, set())
                    files_set.add(path.name)

                    event = entry.get("event")
                    data = entry.get("data", {})
                    counts["events_total"] += 1
                    if event == "song_started":
                        counts["song_started_total"] += 1
                        if data.get("found"):
                            counts["song_found_total"] += 1
                        else:
                            counts["song_fallback_total"] += 1
                    elif event == "error":
                        counts["error_total"] += 1
        except OSError:
            continue

    result = []
    for day in sorted(days.keys(), reverse=True):
        row = {"day": day, "sessions": len(files_per_day.get(day, set()))}
        row.update(dict(days.get(day, Counter())))
        result.append(row)
    return result


def day_detail(stats_dir: Path, day: str) -> dict[str, Any]:
    try:
        y, m, _d = [int(x) for x in day.split("-")]
    except ValueError:
        return {"day": day, "sessions": [], "summary": {}}

    files = _files_for_month(stats_dir, y, m)
    total = Counter()
    sessions: set[str] = set()
    for path in files:
        try:
            with path.open("r", encoding="utf-8") as fh:
                matched = False
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if _parse_ts_to_day(str(entry.get("ts", ""))) != day:
                        continue
                    matched = True
                    event = entry.get("event")
                    data = entry.get("data", {})
                    total["events_total"] += 1
                    if event == "song_started":
                        total["song_started_total"] += 1
                        if data.get("found"):
                            total["song_found_total"] += 1
                        else:
                            total["song_fallback_total"] += 1
                    elif event == "error":
                        total["error_total"] += 1
                if matched:
                    sessions.add(path.name)
        except OSError:
            continue
    return {
        "day": day,
        "sessions": sorted(sessions),
        "summary": dict(total),
    }
