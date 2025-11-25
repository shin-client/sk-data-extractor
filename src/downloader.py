import logging
import zipfile
import requests
import os
import shutil
import stat
from pathlib import Path
from typing import Tuple
from src.config import (
    APK_REGEX, BASE_URL, DATA_DIR,
    ASSET_STUDIO_REPO_API, ASSET_STUDIO_ARTIFACT_REGEX,
    ASSET_STUDIO_DIR, ASSET_STUDIO_ZIP
)

def get_latest_asset_studio_url() -> str:
    """
    Gọi GitHub API để lấy link download AssetStudioModCLI mới nhất cho Linux.
    """
    logging.info(f"Checking for latest AssetStudio release at: {ASSET_STUDIO_REPO_API}")
    try:
        resp = requests.get(ASSET_STUDIO_REPO_API, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        assets = data.get("assets", [])
        for asset in assets:
            name = asset.get("name", "")
            browser_download_url = asset.get("browser_download_url", "")

            # Kiểm tra xem tên file có khớp với pattern linux net9 không
            if ASSET_STUDIO_ARTIFACT_REGEX.search(name):
                logging.info(f"Found latest AssetStudio: {name} ({data.get('tag_name')})")
                return browser_download_url

        # Nếu không tìm thấy file mong muốn
        raise RuntimeError("Could not find AssetStudioModCLI_net9_linux64.zip in the latest release assets.")

    except Exception as e:
        raise RuntimeError(f"Failed to fetch latest AssetStudio release info: {e}") from e

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

def flatten_directory(root_dir: Path, target_file_name: str) -> None:
    """
    Tìm file mục tiêu trong subfolder và di chuyển tất cả nội dung ra root_dir.
    """
    target_path = root_dir / target_file_name
    if target_path.exists():
        return

    found_files = list(root_dir.rglob(target_file_name))
    if not found_files:
        logging.warning(f"Could not find {target_file_name} in {root_dir} (even recursively).")
        return

    actual_file = found_files[0]
    parent_dir = actual_file.parent

    if parent_dir != root_dir:
        logging.info(f"Found nested folder structure at {parent_dir}. Flattening to {root_dir}...")
        for item in parent_dir.iterdir():
            dest = root_dir / item.name
            if dest.exists():
                if dest.is_dir():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()
            shutil.move(str(item), str(root_dir))
        try:
            shutil.rmtree(parent_dir)
        except Exception:
            pass

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

def ensure_asset_studio() -> Path:
    """
    Tự động lấy link mới nhất, tải về, giải nén và setup.
    """
    # Chỉ tải lại nếu file zip chưa tồn tại
    if not ASSET_STUDIO_ZIP.exists():
        latest_url = get_latest_asset_studio_url()
        download_file(latest_url, ASSET_STUDIO_ZIP)

    if not ASSET_STUDIO_DIR.exists():
        extract_zip(ASSET_STUDIO_ZIP, ASSET_STUDIO_DIR)

        # Tên file binary trên Linux (thường không đuôi)
        binary_name = "AssetStudioModCLI"

        # Flatten nếu cần
        flatten_directory(ASSET_STUDIO_DIR, binary_name)

        # Cấp quyền execute
        executable = ASSET_STUDIO_DIR / binary_name
        if executable.exists():
            st = os.stat(executable)
            os.chmod(executable, st.st_mode | stat.S_IEXEC)
            logging.info(f"Granted execute permission to {binary_name}.")
        else:
            # Fallback check
            logging.warning(f"Binary {binary_name} not found after setup.")

    return ASSET_STUDIO_DIR
