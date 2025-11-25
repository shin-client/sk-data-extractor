import logging
import os
import stat
from pathlib import Path
from typing import Tuple
import requests
import zipfile
from src.config import APK_REGEX, BASE_URL, DATA_DIR, ASSET_RIPPER_URL, ASSET_RIPPER_DIR, ASSET_RIPPER_ZIP

def download_file(url: str, dest: Path, chunk_size: int = 8192) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    logging.info(f"Downloading: {url}")
    try:
        with requests.get(url, verify=False, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
    except Exception as e:
        raise RuntimeError(f"Failed to download {url}: {e}") from e

def extract_zip(zip_path: Path, target_dir: Path) -> None:
    if not zip_path.exists():
        raise FileNotFoundError(f"Zip file not found: {zip_path}")
    logging.info(f"Extracting zip: {zip_path} -> {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target_dir)
    except zipfile.BadZipFile as e:
        raise RuntimeError(f"Bad zip file {zip_path}: {e}") from e

def get_latest_apk_info() -> Tuple[str, str]:
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

def ensure_asset_ripper() -> Path:
    """
    Tải, giải nén và cấp quyền thực thi cho AssetRipper.
    """
    if not ASSET_RIPPER_ZIP.exists():
        download_file(ASSET_RIPPER_URL, ASSET_RIPPER_ZIP)

    if not ASSET_RIPPER_DIR.exists():
        extract_zip(ASSET_RIPPER_ZIP, ASSET_RIPPER_DIR)

        # Cấp quyền execute cho file binary AssetRipper (Linux)
        executable = ASSET_RIPPER_DIR / "AssetRipper"
        if executable.exists():
            st = os.stat(executable)
            os.chmod(executable, st.st_mode | stat.S_IEXEC)
            logging.info("Granted execute permission to AssetRipper binary.")

    return ASSET_RIPPER_DIR
