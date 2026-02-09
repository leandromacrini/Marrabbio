from __future__ import annotations

from pathlib import Path
import logging
import queue
import signal
import threading
import time

from .catalog import load_song_catalog
from .config import load_config
from .dialer import DialController
from .player import AudioPlayer
from .stats import StatsRecorder
from .web import StatsWebServer

SONGS_LIST_FILE = "songs.txt"
MEDIA_DIR = "media"
SONGS_DIR = "songs"
SOUNDS_DIR = "sounds"
STATS_DIR = "stats"
DIAL_TONE_FILE = "dial.mp3"
FALLBACK_SONG_FILE = "Utaimashou.mp3"


def _setup_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def run() -> int:
    project_root = Path(__file__).resolve().parent.parent
    config = load_config(project_root)
    _setup_logging(config.logging.level)

    songs_list_file = project_root / SONGS_LIST_FILE
    songs_dir = project_root / MEDIA_DIR / SONGS_DIR
    sounds_dir = project_root / MEDIA_DIR / SOUNDS_DIR
    stats_dir = project_root / STATS_DIR
    dial_tone_file = sounds_dir / DIAL_TONE_FILE
    fallback_song_file = sounds_dir / FALLBACK_SONG_FILE

    logging.info("Starting Marrabbio")

    songs = load_song_catalog(songs_list_file, songs_dir)
    player = AudioPlayer()
    stats = StatsRecorder(stats_dir)
    dial = DialController(
        player=player,
        songs_by_code=songs,
        fallback_song_file=fallback_song_file,
        digit_audio_dir=sounds_dir,
        dial_tone_file=dial_tone_file,
        timing=config.timing,
        stats=stats,
    )
    web = StatsWebServer(
        host=config.web.host,
        port=config.web.port,
        stats_dir=stats_dir,
        get_live_snapshot=stats.snapshot,
        refresh_seconds=config.web.refresh_seconds,
    )
    web.start()
    logging.info("Web dashboard ready on http://%s:%s", config.web.host, config.web.port)

    stop_event = threading.Event()
    events: queue.Queue[tuple[str, float]] = queue.Queue()

    def push(name: str) -> None:
        events.put((name, time.monotonic()))

    def worker() -> None:
        while not stop_event.is_set():
            try:
                name, _ts = events.get(timeout=0.2)
            except queue.Empty:
                continue

            if name == "hook_on":
                dial.on_hook_lifted()
            elif name == "hook_off":
                dial.on_hook_replaced()
            elif name == "rotary_start":
                dial.on_rotary_engaged()
            elif name == "rotary_stop":
                dial.on_rotary_released()
            elif name == "pulse":
                dial.on_rotary_pulse()

            events.task_done()

    worker_thread = threading.Thread(target=worker, name="marrabbio-events", daemon=True)
    worker_thread.start()

    if config.runtime.gpio_enabled:
        try:
            import gpiozero
            from gpiozero import Device

            logging.info("gpiozero pin factory: %s", Device.pin_factory)
            rotary_enable = gpiozero.Button(
                config.pins.rotary_enable,
                pull_up=False,
                bounce_time=config.debounce.rotary_enable,
            )
            rotary_pulse = gpiozero.Button(
                config.pins.rotary_pulse,
                pull_up=False,
                bounce_time=config.debounce.rotary_pulse,
            )
            hook = gpiozero.Button(
                config.pins.hook,
                pull_up=False,
                bounce_time=config.debounce.hook,
            )

            hook.when_activated = lambda: push("hook_on")
            hook.when_deactivated = lambda: push("hook_off")
            rotary_enable.when_activated = lambda: push("rotary_start")
            rotary_enable.when_deactivated = lambda: push("rotary_stop")
            rotary_pulse.when_activated = lambda: push("pulse")
        except Exception as exc:
            stats.record_error("gpio_init_failed", str(exc))
            logging.exception("GPIO init failed, running in web-only mode")
    else:
        logging.info("GPIO disabled by config, running in web-only mode")

    def shutdown(*_args: object) -> None:
        logging.info("Shutdown signal received")
        stop_event.set()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while not stop_event.is_set():
            time.sleep(0.5)
    finally:
        web.stop()
        stats.close()
        player.stop()
        logging.info("Marrabbio stopped")

    return 0
