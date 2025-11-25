import re
from pathlib import Path
from typing import List, Tuple, Optional
from .utils import sanitize_text
from .config import LANGUAGES


def parse_i2_asset_file(
    file_path: Path, filter_patterns: Optional[List[re.Pattern[str]]] = None
) -> Tuple[List[Tuple[str, List[str]]], List[str]]:
    """
    Parse a single I2 Languages .dat file.
    Returns:
      - sorted list of (key, [fields...])
      - list of language names
    """
    if not file_path.exists():
        raise FileNotFoundError(f"I2 .dat file not found: {file_path}")

    data = file_path.read_bytes()
    records: List[Tuple[str, List[str]]] = []
    pos = 60

    while pos < len(data):

        if pos % 4:
            pos += 4 - (pos % 4)
        if pos + 4 > len(data):
            break

        key_len = int.from_bytes(data[pos : pos + 4], "little")
        pos += 4

        if key_len == 0:

            while (
                pos < len(data) and int.from_bytes(data[pos : pos + 4], "little") == 0
            ):
                pos += 4
            if pos >= len(data) - 4:
                break
            key_len = int.from_bytes(data[pos : pos + 4], "little")
            pos += 4
            if key_len == 0:
                break

        key_bytes = data[pos : pos + key_len]
        try:
            key = key_bytes.decode("utf-8", errors="ignore").strip()
        except UnicodeDecodeError:
            key = key_bytes.decode("latin-1", errors="ignore").strip()
        pos += key_len

        if pos % 4:
            pos += 4 - (pos % 4)

        if pos + 4 > len(data):
            break
        start_count = int.from_bytes(data[pos : pos + 4], "little")
        pos += 4

        if start_count == 0:
            if pos + 4 > len(data):
                break
            fields_count = int.from_bytes(data[pos : pos + 4], "little")
            pos += 4
        else:
            fields_count = start_count

        fields: List[str] = []
        for _ in range(fields_count):
            if pos + 4 > len(data):
                break
            field_len = int.from_bytes(data[pos : pos + 4], "little")
            pos += 4

            if field_len > 0:
                raw = data[pos : pos + field_len]
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    text = raw.decode("latin-1", errors="ignore")
            else:
                text = ""
            fields.append(sanitize_text(text))
            pos += field_len

            if pos % 4:
                pos += 4 - (pos % 4)

        if pos + 4 <= len(data):
            pos += 4

        if not filter_patterns or not any(p.match(key) for p in filter_patterns):
            records.append((key, fields))

    records.sort(key=lambda r: r[0])
    return records, LANGUAGES
