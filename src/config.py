from pathlib import Path
import re
from typing import List

BASE_URL = "http://www.chillyroom.com/zh"
APK_REGEX = re.compile(
    r"https://apk\.chillyroom\.com/apks/[\w\d.\-]+/SoulKnight-release-chillyroom-([\w\d.\-]+)\.apk"
)

ASSET_RIPPER_URL = "https://github.com/AssetRipper/AssetRipper/releases/download/1.3.6/AssetRipper_linux_x64.zip"

LANGUAGES: List[str] = [
    "English",
    "Chinese (Traditional)",
    "Chinese (Simplified)",
    "Vietnamese",
]

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
EXPORT_DIR = DATA_DIR / "export"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Thư mục chứa tool
ASSET_RIPPER_DIR = DATA_DIR / "AssetRipper"
ASSET_RIPPER_ZIP = DATA_DIR / "AssetRipper.zip"
