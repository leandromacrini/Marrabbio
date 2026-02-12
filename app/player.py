from __future__ import annotations

from pathlib import Path
import logging
import subprocess
from typing import Sequence


class AudioPlayer:
    def __init__(self) -> None:
        self._process: subprocess.Popen | None = None

    def _spawn(self, args: Sequence[str]) -> None:
        self.stop()
        self._process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def play_file(self, audio_file: Path, loop_count: int | None = None) -> None:
        if not audio_file.exists():
            logging.error("Audio file not found: %s", audio_file)
            return

        command = ["mpg123"]
        if loop_count is not None:
            command += ["--loop", str(loop_count)]
        command += ["-q", str(audio_file)]
        logging.info("Playing: %s", audio_file.name)
        self._spawn(command)

    def play_file_blocking(self, audio_file: Path) -> None:
        if not audio_file.exists():
            logging.error("Audio file not found: %s", audio_file)
            return
        self.stop()
        subprocess.run(["mpg123", "-q", str(audio_file)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

    def play_sequence_blocking(self, files: Sequence[Path]) -> None:
        self.stop()
        for audio_file in files:
            if not audio_file.exists():
                logging.error("Audio file not found: %s", audio_file)
                continue
            subprocess.run(["mpg123", "-q", str(audio_file)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

    def stop(self) -> None:
        if self._process is None:
            return
        try:
            self._process.kill()
        except OSError:
            pass
        finally:
            self._process = None
