from pathlib import Path
import re
from typing import List

BASE_URL = "http://www.chillyroom.com/zh"
APK_REGEX = re.compile(
    r"https://apk\.chillyroom\.com/apks/[\w\d.\-]+/SoulKnight-release-chillyroom-([\w\d.\-]+)\.apk"
)

ASSET_STUDIO_CLI_URL = (
    "https://github.com/aelurum/AssetStudio/releases/download/"
    "v0.19.0/AssetStudioModCLI_net9_linux64.zip"
)

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

# AssetStudio Paths
ASSET_STUDIO_DIR = DATA_DIR / "AssetStudio"
ASSET_STUDIO_ZIP = DATA_DIR / "AssetStudio.zip"
