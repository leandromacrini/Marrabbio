from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import logging
import socket
import subprocess
import threading
from pathlib import Path

from .config import Timing
from .player import AudioPlayer
from .stats import StatsRecorder


class DialState(Enum):
    IDLE = "idle"
    OFF_HOOK = "off_hook"
    DIALING = "dialing"
    PLAYING = "playing"


@dataclass
class DialContext:
    pulses: int = 0
    typed_number: str = ""


class DialController:
    SPECIAL_PREFIX = "000"
    SPECIAL_CODE_LENGTH = 5
    CODE_IP = "00001"
    CODE_REBOOT = "00008"
    CODE_SHUTDOWN = "00009"

    def __init__(
        self,
        player: AudioPlayer,
        songs_by_code: dict[str, Path],
        fallback_song_file: Path,
        digit_audio_dir: Path,
        media_dir: Path,
        dial_tone_file: Path,
        timing: Timing,
        stats: StatsRecorder,
    ) -> None:
        self._player = player
        self._songs = songs_by_code
        self._fallback_song_file = fallback_song_file
        self._digit_audio_dir = digit_audio_dir
        self._media_dir = media_dir
        self._dial_tone_file = dial_tone_file
        self._timing = timing
        self._stats = stats

        self._state = DialState.IDLE
        self._ctx = DialContext()
        self._lock = threading.Lock()
        self._pending_song_timer: threading.Timer | None = None

    def _cancel_pending_song_timer(self) -> None:
        if self._pending_song_timer is not None:
            self._pending_song_timer.cancel()
            self._pending_song_timer = None

    def on_hook_lifted(self) -> None:
        with self._lock:
            logging.info("Hook lifted")
            self._cancel_pending_song_timer()
            self._ctx = DialContext()
            self._state = DialState.OFF_HOOK
        self._player.play_file(self._dial_tone_file, loop_count=self._timing.dial_tone_loop_count)

    def on_hook_replaced(self) -> None:
        with self._lock:
            logging.info("Hook replaced")
            self._cancel_pending_song_timer()
            self._ctx = DialContext()
            self._state = DialState.IDLE
        self._player.stop()

    def on_rotary_engaged(self) -> None:
        with self._lock:
            if self._state in (DialState.OFF_HOOK, DialState.PLAYING):
                if self._state == DialState.PLAYING:
                    logging.info("Dial started during playback: auto-reset current song")
                    self._cancel_pending_song_timer()
                    self._player.stop()
                self._state = DialState.DIALING
                self._ctx.pulses = 0
                logging.info("Rotary engaged")

    def on_rotary_pulse(self) -> None:
        with self._lock:
            if self._state == DialState.DIALING:
                self._ctx.pulses += 1
                logging.debug("Pulse %s", self._ctx.pulses)

    def on_rotary_released(self) -> None:
        with self._lock:
            if self._state != DialState.DIALING:
                return

            pulses = self._ctx.pulses
            self._ctx.pulses = 0
            self._state = DialState.OFF_HOOK

        digit = self._digit_from_pulses(pulses)
        if digit is None:
            if pulses > 0:
                logging.warning("Ignored unexpected pulses count: %s", pulses)
                self._stats.record_error("invalid_pulse_group", f"pulses={pulses}")
            return

        with self._lock:
            self._ctx.typed_number += digit
            number = self._ctx.typed_number
            logging.info("Dialed so far: %s", number)
            completed = self._is_code_complete(number)
            if completed:
                self._state = DialState.PLAYING

        self._play_digit_feedback(digit)

        if completed:
            timer = threading.Timer(self._timing.play_song_delay_sec, self._play_selected_song, args=(number,))
            with self._lock:
                self._pending_song_timer = timer
            timer.start()

    def _play_digit_feedback(self, digit: str) -> None:
        digit_file = self._digit_audio_dir / f"{digit}.mp3"
        self._player.play_file(digit_file)

    def _play_selected_song(self, code: str) -> None:
        with self._lock:
            self._pending_song_timer = None
            if self._state != DialState.PLAYING:
                return
            self._state = DialState.PLAYING
            self._ctx = DialContext()

        if code == self.CODE_IP:
            self._play_ip_address()
            return
        if code == self.CODE_REBOOT:
            self._play_and_system_action("Ributto.mp3", ["systemctl", "reboot"], "reboot")
            return
        if code == self.CODE_SHUTDOWN:
            self._play_and_system_action("Shattodaun.mp3", ["systemctl", "poweroff"], "shutdown")
            return

        song_file = self._songs.get(code, self._fallback_song_file)
        if song_file == self._fallback_song_file:
            logging.warning("Song code not found: %s, using fallback", code)
            self._stats.record_song_started(code=code, found=False, title=self._fallback_song_file.stem)
        else:
            logging.info("Matched song code %s", code)
            self._stats.record_song_started(code=code, found=True, title=song_file.stem)
        if not song_file.exists():
            self._stats.record_error("missing_song_file", str(song_file))
        self._player.play_file(song_file)

    @staticmethod
    def _digit_from_pulses(pulses: int) -> str | None:
        if pulses == 10:
            return "0"
        if 1 <= pulses <= 9:
            return str(pulses)
        return None

    def _is_code_complete(self, number: str) -> bool:
        if number == self.SPECIAL_PREFIX:
            return False
        if number.startswith(self.SPECIAL_PREFIX):
            return len(number) == self.SPECIAL_CODE_LENGTH
        return len(number) == self._timing.expected_digits

    def _play_ip_address(self) -> None:
        intro = self._media_dir / "IPaddresso.mp3"
        point = self._media_dir / "Pointo.mp3"
        sequence = [intro]
        ip = self._resolve_local_ip()
        octets = ip.split(".")

        for i, octet in enumerate(octets):
            for ch in octet:
                sequence.append(self._digit_audio_dir / f"{ch}.mp3")
            if i < len(octets) - 1:
                sequence.append(point)

        self._player.play_sequence_blocking(sequence)
        logging.info("Announced IP address: %s", ip)

    def _play_and_system_action(self, audio_name: str, command: list[str], action_name: str) -> None:
        self._player.play_file_blocking(self._media_dir / audio_name)
        logging.info("Running system action: %s", action_name)
        if self._run_system_command(command):
            return
        self._stats.record_error("system_action_failed", f"{action_name}:{' '.join(command)}")
        logging.error("System action failed: %s", action_name)
        with self._lock:
            if self._state == DialState.PLAYING:
                self._state = DialState.OFF_HOOK

    def _run_system_command(self, command: list[str]) -> bool:
        attempts = [
            command,
            ["sudo", "-n", *command],
        ]
        for cmd in attempts:
            try:
                completed = subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                if completed.returncode == 0:
                    return True
            except OSError:
                continue
        return False

    @staticmethod
    def _resolve_local_ip() -> str:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and ip != "0.0.0.0":
                return ip
        except OSError:
            pass
        finally:
            sock.close()
        return "0.0.0.0"
