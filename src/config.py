from pathlib import Path
import re
from typing import List

BASE_URL = "http://www.chillyroom.com/zh"
APK_REGEX = re.compile(
    r"https://apk\.chillyroom\.com/apks/[\w\d.\-]+/SoulKnight-release-chillyroom-([\w\d.\-]+)\.apk"
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
