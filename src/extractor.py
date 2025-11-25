import logging
import subprocess
from pathlib import Path
from typing import List, Optional
from .config import EXPORT_DIR, ASSET_STUDIO_DIR, RAW_DUMP_DIR


def run_asset_studio_cli(
    unity_data_path: Path,
    output_dir: Path,
    asset_type: str,
    mode: str,
    filter_name: str,
    assembly_folder: Path | None = None,
    extra_args: Optional[List[str]] = None,
) -> None:
    """
    Hàm gọi AssetStudioModCLI thông qua subprocess.
    """
    if not unity_data_path.exists():
        raise FileNotFoundError(f"Unity data file not found: {unity_data_path}")

    # Tìm file thực thi
    # 1. Tìm trực tiếp tại root (Trường hợp lý tưởng sau khi flatten)
    executable = ASSET_STUDIO_DIR / "AssetStudioModCLI"

    # 2. Nếu không thấy, tìm đệ quy (Trường hợp flatten lỗi)
    if not executable.exists():
        found = list(ASSET_STUDIO_DIR.rglob("AssetStudioModCLI"))
        if found:
            executable = found[0]
            logging.info(f"Found binary in nested folder: {executable}")

    # 3. Fallback cho bản Windows (.exe)
    if not executable.exists():
        executable = ASSET_STUDIO_DIR / "AssetStudioModCLI.exe"
        if not executable.exists():
            # Thử tìm exe đệ quy
            found_exe = list(ASSET_STUDIO_DIR.rglob("AssetStudioModCLI.exe"))
            if found_exe:
                executable = found_exe[0]

    if not executable.exists():
        raise FileNotFoundError(
            f"AssetStudioModCLI binary not found in {ASSET_STUDIO_DIR} or subfolders"
        )

    cmd = [
        str(executable),
        str(unity_data_path),
        "-t",
        asset_type,
        "-m",
        mode,
        "-o",
        str(output_dir),
    ]

    if filter_name:
        cmd.extend(["--filter-by-name", filter_name])

    if assembly_folder:
        if not assembly_folder.exists():
            logging.warning(f"Assembly folder not found: {assembly_folder}")
        else:
            cmd.extend(["--assembly-folder", str(assembly_folder)])

    # Thêm các tham số phụ (như --json, --image-format, v.v.)
    if extra_args:
        cmd.extend(extra_args)

    logging.info(
        f"Running AssetStudio CLI (Type: {asset_type}, Filter: '{filter_name}')..."
    )

    try:
        # cwd là thư mục chứa file thực thi để nó load được DLL
        subprocess.run(cmd, check=True, cwd=str(executable.parent))
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"AssetStudioModCLI failed with exit code {e.returncode}"
        ) from e

    logging.info(f"Finished extracting/dumping {asset_type}.")


def run_asset_extractions(sk_extracted_path: Path) -> None:
    """
    Chạy AssetStudio để trích xuất dữ liệu.
    """
    assets_root = sk_extracted_path / "assets"
    unity_data = sk_extracted_path / "assets/bin/Data/data.unity3d"
    managed_folder = sk_extracted_path / "assets/bin/Data/Managed"

    if not unity_data.exists():
        raise FileNotFoundError(f"Unity data file missing: {unity_data}")

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DUMP_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Extract I2Languages
    run_asset_studio_cli(
        unity_data_path=unity_data,
        output_dir=EXPORT_DIR,
        asset_type="monobehaviour",
        mode="raw",
        filter_name="i2language",
        assembly_folder=managed_folder,
    )

    # Xóa file rác
    for dat_file in EXPORT_DIR.rglob("I2Languages*.dat"):
        if dat_file.stat().st_size < 2_000_000:
            try:
                dat_file.unlink()
            except Exception:
                pass

    # 2. Extract WeaponInfo
    logging.info("--- Step 2: Extracting WeaponInfo ---")
    run_asset_studio_cli(
        unity_data_path=unity_data,
        output_dir=EXPORT_DIR,
        asset_type="textasset",
        mode="export",
        filter_name="WeaponInfo",
    )

    # --- 3. DUMP TOÀN BỘ TEXT ASSET (Tìm file config ẩn) ---
    # Xuất ra thư mục: data/raw_dump/TextAsset
    logging.info("--- Step 3: Dumping ALL TextAssets (Configs, XMLs, JSONs) ---")
    text_asset_dir = RAW_DUMP_DIR / "TextAsset"
    text_asset_dir.mkdir(exist_ok=True)

    run_asset_studio_cli(
        unity_data_path=assets_root,  # Quét cả thư mục assets để tìm file trong .ab
        output_dir=text_asset_dir,
        asset_type="TextAsset",
        mode="export",  # Export nội dung text
        filter_name="",  # Rỗng = Lấy tất cả
        # extra_args=["--group-by-type"] # Tuỳ chọn: gom nhóm folder (nếu CLI hỗ trợ)
    )

    # --- 4. DUMP TOÀN BỘ MONOBEHAVIOUR (Chỉ số Game) ---
    # Xuất ra thư mục: data/raw_dump/MonoBehaviour
    # Lưu ý: Cần assembly_folder để giải mã tên biến
    logging.info("--- Step 4: Dumping ALL MonoBehaviours (Game Stats) ---")
    mono_dir = RAW_DUMP_DIR / "MonoBehaviour"
    mono_dir.mkdir(exist_ok=True)

    run_asset_studio_cli(
        unity_data_path=assets_root,  # Quét cả thư mục assets
        output_dir=mono_dir,
        asset_type="MonoBehaviour",
        mode="dump",  # Mode dump sẽ tạo ra file json/txt cấu trúc dữ liệu
        filter_name="",  # Rỗng = Lấy tất cả
        assembly_folder=managed_folder,
        extra_args=["--json"],  # Thử ép xuất ra JSON (nếu CLI hỗ trợ flag này)
    )

    logging.info(f"Full raw dump completed. Check folder: {RAW_DUMP_DIR}")
