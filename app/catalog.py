from __future__ import annotations

from pathlib import Path
import logging


def load_song_catalog(songs_file: Path, songs_dir: Path) -> dict[str, Path]:
    songs: dict[str, Path] = {}
    with songs_file.open("r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) < 2:
                logging.warning("Invalid songs line %s: %s", line_no, line)
                continue

            song_code = parts[0]
            song_name = " ".join(parts[1:])
            songs[song_code] = songs_dir / f"{song_name}.mp3"

    logging.info("Loaded %s songs from %s", len(songs), songs_file)
    return songs

