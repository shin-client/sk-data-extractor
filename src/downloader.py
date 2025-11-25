import logging
from pathlib import Path
from typing import Tuple
import zipfile
from .config import DATA_DIR

import requests

from src.config import APK_REGEX, BASE_URL


def download_file(url: str, dest: Path, chunk_size: int = 8192) -> None:
    """
    Download `url` to `dest` with a custom progress bar, download speed, and ETA.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    logging.info(f"Downloading: {url}")

    try:
        with requests.get(url, verify=False, stream=True, timeout=30) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
    except Exception as e:
        raise RuntimeError(f"Failed to download {url}: {e}") from e


def get_latest_apk_info() -> Tuple[str, str]:
    """
    Fetch BASE_URL, search for APK_REGEX. Return (version, download_link).
    Raises RuntimeError if not found.
    """
    logging.info(f"Fetching website: {BASE_URL}")
    try:
        resp = requests.get(BASE_URL, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Failed to fetch {BASE_URL}: {e}") from e

    match = APK_REGEX.search(resp.text)
    if not match:
        raise RuntimeError("Could not find Soul Knight APK link on page.")
    version = match.group(1)
    link = match.group(0)
    logging.info(f"Found version: {version}")
    return version, link


def ensure_apk_extracted(version: str, link: str) -> Path:
    """
    Download APK và giải nén. Trả về đường dẫn folder đã giải nén.
    """
    versioned_apk_file = DATA_DIR / f"sk-{version}.apk"
    sk_extracted_path = DATA_DIR / f"sk-{version}"

    if not versioned_apk_file.exists():
        download_file(link, versioned_apk_file)

    if not sk_extracted_path.exists():
        logging.info(f"Extracting APK to {sk_extracted_path}...")
        try:
            sk_extracted_path.mkdir(parents=True, exist_ok=False)
            with zipfile.ZipFile(versioned_apk_file, "r") as zf:
                zf.extractall(sk_extracted_path)
        except Exception as e:
            raise RuntimeError(f"Failed extracting APK: {e}") from e

    return sk_extracted_path
