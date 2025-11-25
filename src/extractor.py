import logging
import subprocess
from pathlib import Path
from .config import EXPORT_DIR, ASSET_STUDIO_DIR


def run_asset_studio_cli(
    unity_data_path: Path,
    output_dir: Path,
    asset_type: str,
    mode: str,
    filter_name: str,
    assembly_folder: Path | None = None,
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

    # Xây dựng câu lệnh CLI
    # Với .NET Core/5/6+, ta có thể chạy trực tiếp binary nếu đã chmod +x
    cmd = [
        str(executable),
        str(unity_data_path),
        "-t",
        asset_type,
        "-m",
        mode,
        "-o",
        str(output_dir),
        "--filter-by-name",
        filter_name,
    ]

    if assembly_folder:
        if not assembly_folder.exists():
            logging.warning(f"Assembly folder not found: {assembly_folder}")
        else:
            cmd.extend(["--assembly-folder", str(assembly_folder)])

    logging.info(f"Running AssetStudio CLI for {filter_name}...")

    try:
        # cwd là thư mục chứa file thực thi để nó load được DLL
        subprocess.run(cmd, check=True, cwd=str(executable.parent))
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"AssetStudioModCLI failed with exit code {e.returncode}"
        ) from e

    logging.info(f"Finished extracting {filter_name}.")


def run_asset_extractions(sk_extracted_path: Path) -> None:
    """
    Chạy AssetStudio để trích xuất dữ liệu.
    """
    unity_data = sk_extracted_path / "assets/bin/Data/data.unity3d"
    managed_folder = sk_extracted_path / "assets/bin/Data/Managed"

    if not unity_data.exists():
        raise FileNotFoundError(f"Unity data file missing: {unity_data}")

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

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

    # 2. Extract WeaponInfo (Vẫn giữ logic cũ)
    run_asset_studio_cli(
        unity_data_path=unity_data,
        output_dir=EXPORT_DIR,
        asset_type="textasset",
        mode="export",
        filter_name="WeaponInfo",
    )

    # --- BƯỚC MỚI: Liệt kê tất cả TextAsset để tìm CharacterData/HeroConfig ---
    # Ta chạy chế độ 'info' (hoặc export dummy) để xem danh sách file
    # Vì AssetStudioModCLI không có chế độ 'list' thuần túy dễ đọc,
    # ta sẽ thử export TOÀN BỘ TextAsset nhưng lọc theo tên chung chung
    # hoặc đơn giản là export hết TextAsset ra một folder riêng để bạn kiểm tra artifact

    logging.info("--- SCANNING FOR INTERESTING TEXT ASSETS ---")
    debug_export_dir = EXPORT_DIR / "DebugTextAssets"
    debug_export_dir.mkdir(parents=True, exist_ok=True)

    # Tìm các file có từ khóa tiềm năng
    interesting_keywords = "Character,Hero,Config,Data,Global,Manager"

    run_asset_studio_cli(
        unity_data_path=unity_data,
        output_dir=debug_export_dir,
        asset_type="textasset",
        mode="export",
        filter_name=interesting_keywords,  # Lọc nhiều từ khóa cùng lúc
    )

    # Liệt kê các file tìm được ra log để bạn xem tên chính xác
    logging.info("--- FOUND POTENTIAL FILES ---")
    found_files = list(debug_export_dir.rglob("*.txt"))
    for f in found_files:
        logging.info(f"Found: {f.name}")

    logging.info("-----------------------------")
