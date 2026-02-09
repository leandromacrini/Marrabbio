from __future__ import annotations

from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from .stats import day_detail, list_calendar_for_month, top_songs_all_time, top_songs_for_day


class StatsWebServer:
    def __init__(
        self,
        host: str,
        port: int,
        stats_dir: Path,
        get_live_snapshot: Callable[[], dict[str, Any]],
        refresh_seconds: int,
    ) -> None:
        self._host = host
        self._port = port
        self._stats_dir = stats_dir
        self._get_live_snapshot = get_live_snapshot
        self._refresh_seconds = refresh_seconds
        self._static_dir = Path(__file__).resolve().parent.parent / "ui"
        self._server = ThreadingHTTPServer((host, port), self._make_handler())
        self._thread: threading.Thread | None = None

    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        stats_dir = self._stats_dir
        get_live_snapshot = self._get_live_snapshot
        static_dir = self._static_dir
        refresh_seconds = self._refresh_seconds

        class Handler(BaseHTTPRequestHandler):
            def _write_json(self, payload: dict[str, Any], status: int = 200) -> None:
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _write_file(self, file_path: Path, content_type: str, status: int = 200) -> None:
                if not file_path.exists() or not file_path.is_file():
                    self._write_json({"error": "not found"}, status=404)
                    return
                data = file_path.read_bytes()
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                path = parsed.path
                q = parse_qs(parsed.query)

                if path == "/":
                    self._write_file(static_dir / "index.html", "text/html; charset=utf-8")
                    return

                if path == "/static/styles.css":
                    self._write_file(static_dir / "styles.css", "text/css; charset=utf-8")
                    return

                if path == "/static/app.js":
                    self._write_file(static_dir / "app.js", "application/javascript; charset=utf-8")
                    return

                if path == "/api/live":
                    self._write_json(get_live_snapshot())
                    return

                if path == "/api/calendar":
                    now = datetime.utcnow()
                    try:
                        year = int(q.get("year", [now.year])[0])
                    except (TypeError, ValueError):
                        year = now.year
                    try:
                        month = int(q.get("month", [now.month])[0])
                    except (TypeError, ValueError):
                        month = now.month
                    if month < 1 or month > 12:
                        month = now.month
                    self._write_json({"year": year, "month": month, "days": list_calendar_for_month(stats_dir, year, month)})
                    return

                if path == "/api/top/all":
                    self._write_json({"items": top_songs_all_time(stats_dir)})
                    return

                if path.startswith("/api/top/day/"):
                    day = path.split("/", 4)[4]
                    self._write_json({"day": day, "items": top_songs_for_day(stats_dir, day)})
                    return

                if path.startswith("/api/day/"):
                    day = path.split("/", 3)[3]
                    self._write_json(day_detail(stats_dir, day))
                    return

                if path == "/api/config":
                    self._write_json({"refresh_seconds": refresh_seconds})
                    return

                self._write_json({"error": "not found"}, status=404)

            def log_message(self, _format: str, *_args: object) -> None:
                return

        return Handler

    def start(self) -> None:
        self._thread = threading.Thread(target=self._server.serve_forever, name="marrabbio-web", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
