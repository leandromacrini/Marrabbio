from __future__ import annotations

from dataclasses import dataclass
import tomllib


@dataclass(frozen=True)
class Pins:
    rotary_enable: int = 5
    rotary_pulse: int = 6
    hook: int = 21


@dataclass(frozen=True)
class Debounce:
    rotary_enable: float = 0.01
    rotary_pulse: float = 0.004
    hook: float = 0.02


@dataclass(frozen=True)
class Timing:
    play_song_delay_sec: float = 0.75
    dial_tone_loop_count: int = 20
    expected_digits: int = 3


@dataclass(frozen=True)
class Logging:
    level: str = "INFO"


@dataclass(frozen=True)
class Web:
    host: str = "0.0.0.0"
    port: int = 80
    refresh_seconds: int = 2


@dataclass(frozen=True)
class Runtime:
    gpio_enabled: bool = True


@dataclass(frozen=True)
class AppConfig:
    pins: Pins
    debounce: Debounce
    timing: Timing
    logging: Logging
    web: Web
    runtime: Runtime


def _load_toml(path: str) -> dict:
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return {}
    with p.open("rb") as f:
        return tomllib.load(f)


def _as_bool(value: object, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    return text in ("1", "true", "yes", "on")


def load_config(project_root) -> AppConfig:
    from pathlib import Path

    config_file = str(Path(project_root) / "config.toml")
    data = _load_toml(config_file)

    pins_data = data.get("pins", {})
    debounce_data = data.get("debounce", {})
    timing_data = data.get("timing", {})
    logging_data = data.get("logging", {})
    web_data = data.get("web", {})
    runtime_data = data.get("runtime", {})

    pins = Pins(
        rotary_enable=int(pins_data.get("rotary_enable", 5)),
        rotary_pulse=int(pins_data.get("rotary_pulse", 6)),
        hook=int(pins_data.get("hook", 21)),
    )

    debounce = Debounce(
        rotary_enable=float(debounce_data.get("rotary_enable", 0.01)),
        rotary_pulse=float(debounce_data.get("rotary_pulse", 0.004)),
        hook=float(debounce_data.get("hook", 0.02)),
    )

    timing = Timing(
        play_song_delay_sec=float(timing_data.get("play_song_delay_sec", 0.75)),
        dial_tone_loop_count=int(timing_data.get("dial_tone_loop_count", 20)),
        expected_digits=int(timing_data.get("expected_digits", 3)),
    )
    logging_cfg = Logging(level=str(logging_data.get("level", "INFO")).upper())
    web = Web(
        host=str(web_data.get("host", "0.0.0.0")),
        port=int(web_data.get("port", 80)),
        refresh_seconds=int(web_data.get("refresh_seconds", 2)),
    )
    runtime = Runtime(gpio_enabled=_as_bool(runtime_data.get("gpio_enabled", True), default=True))

    return AppConfig(pins=pins, debounce=debounce, timing=timing, logging=logging_cfg, web=web, runtime=runtime)
