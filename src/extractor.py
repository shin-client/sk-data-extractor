import logging
import zipfile
import subprocess
from pathlib import Path
from typing import Any
import UnityPy
from .config import EXPORT_DIR


def extract_zip(zip_path: Path, target_dir: Path) -> None:
    """
    Extract a zipfile to `target_dir`.
    """
    if not zip_path.exists():
        raise FileNotFoundError(f"Zip file not found: {zip_path}")
    logging.info(f"Extracting zip: {zip_path} → {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target_dir)
    except zipfile.BadZipFile as e:
        raise RuntimeError(f"Bad zip file {zip_path}: {e}") from e
    logging.info("Extraction complete.")


def run_asset_studio_cli(
    asset_studio_dir: Path,
    unity_data_path: Path,
    output_dir: Path,
    asset_type: str,
    mode: str,
    filter_name: str,
    assembly_folder: Path | None = None,
) -> None:
    """
    Invoke AssetStudioModCLI with subprocess.
    - `asset_type`: e.g. "monobehaviour" or "textasset"
    - `mode`: e.g. "raw" or "export"
    - `filter_name`: e.g. "i2language" or "WeaponInfo"
    - `assembly_folder`: required only for monobehaviour extraction.
    """
    if not unity_data_path.exists():
        raise FileNotFoundError(f"Unity data file not found: {unity_data_path}")

    executable = asset_studio_dir / "AssetStudioModCLI.exe"
    if not executable.exists():
        executable = asset_studio_dir / "AssetStudioModCLI"
        if not executable.exists():
            raise FileNotFoundError(
                f"AssetStudioModCLI not found in {asset_studio_dir}"
            )

    cmd: list[str] = [
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
        if not assembly_folder.exists() or not assembly_folder.is_dir():
            raise FileNotFoundError(f"Assembly folder not found: {assembly_folder}")
        cmd.extend(["--assembly-folder", str(assembly_folder)])

    logging.info("Running AssetStudioModCLI: " + " ".join(cmd))
    try:
        subprocess.run(cmd, check=True, cwd=str(asset_studio_dir))
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"AssetStudioModCLI failed (exit code {e.returncode})"
        ) from e
    logging.info(f"AssetStudio CLI finished extracting {asset_type}.")


def run_asset_extractions(sk_extracted_path: Path) -> None:
    """
    Sử dụng UnityPy để quét assets.
    - Tìm I2Languages dựa trên kích thước file.
    - Tìm WeaponInfo dựa trên nội dung JSON (do tên file có thể bị mất).
    """
    assets_root: Path = sk_extracted_path / "assets"

    files_to_load: list[str] = []

    # Chiến thuật 1: Load toàn bộ file trong thư mục Data (nơi chứa assets chính)
    data_dir: Path = assets_root / "bin" / "Data"
    if data_dir.exists():
        # Load tất cả file, bất kể đuôi gì
        files_to_load.extend([str(p) for p in data_dir.glob("*") if p.is_file()])

    # Chiến thuật 2: Fallback quét recursive nếu cấu trúc folder lạ
    if not files_to_load:
        patterns: list[str] = ["*.assets", "*.unity3d", "*.resource", "*.bundle", "globalgamemanagers", "data.unity3d"]
        if assets_root.exists():
            for pattern in patterns:
                files_to_load.extend([str(p) for p in assets_root.rglob(pattern)])
            # Thêm resources (file không đuôi)
            files_to_load.extend([str(p) for p in assets_root.rglob("resources") if p.is_file()])

    # Loại bỏ trùng lặp
    files_to_load = list(set(files_to_load))

    if not files_to_load:
        raise RuntimeError("No Unity asset files found in the extracted APK!")

    logging.info(f"Loading {len(files_to_load)} asset files via UnityPy...")

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Load environment
    env: Any = UnityPy.load(*files_to_load)

    found_i2: bool = False
    found_weapon: bool = False

    obj_stats: dict[str, int] = {}

    obj: Any
    for obj in env.objects:
        type_str: str = str(obj.type.name) if hasattr(obj, "type") else "Unknown"
        obj_stats[type_str] = obj_stats.get(type_str, 0) + 1

        # --- 1. Xử lý TextAsset (ClassID 49) ---
        if obj.type.name == "TextAsset":
            try:
                data: Any = obj.read()
                # Lấy tên (có thể là Unknown)
                name: str = data.name if hasattr(data, "name") and data.name else "Unknown"

                # Cách 1: Tìm theo tên chuẩn (Ưu tiên)
                if name == "WeaponInfo":
                    output_path: Path = EXPORT_DIR / "WeaponInfo.txt"
                    logging.info(f"✅ Found WeaponInfo by NAME. Exporting to {output_path}")
                    if hasattr(data, "script"):
                        script_data: bytes = (
                            data.script
                            if isinstance(data.script, bytes)
                            else data.script.encode("utf-8")
                        )
                        with open(output_path, "wb") as f:
                            f.write(script_data)
                        found_weapon = True

                # Cách 2: Tìm theo nội dung (Fallback)
                # Nếu chưa tìm thấy và script có dữ liệu
                elif not found_weapon and hasattr(data, "script") and data.script:
                    # Kiểm tra chữ ký đặc trưng của WeaponInfo JSON
                    # Nó phải chứa key "weapons" và "forgeable"
                    # data.script là bytes, nên ta so sánh với bytes string
                    script_bytes: bytes = (
                        data.script
                        if isinstance(data.script, bytes)
                        else data.script.encode("utf-8")
                    )
                    content_preview: bytes = script_bytes[:2000]  # Chỉ check header để nhanh
                    if b'"weapons"' in content_preview and b'"forgeable"' in content_preview:
                        output_path: Path = EXPORT_DIR / "WeaponInfo.txt"
                        logging.info(f"✅ Found WeaponInfo by CONTENT (Name was: {name}). Exporting to {output_path}")
                        with open(output_path, "wb") as f:
                            f.write(script_bytes)
                        found_weapon = True

            except Exception as e:
                logging.warning(f"Error reading TextAsset: {e}")

        # --- 2. Xử lý MonoBehaviour (ClassID 114) - I2Languages ---
        elif obj.type.name == "MonoBehaviour":
            # Kiểm tra kích thước trước khi get_raw_data để tối ưu
            byte_size: int = getattr(obj, "byte_size", 0)
            if byte_size > 2_000_000:
                raw_data: bytes = obj.get_raw_data()
                if len(raw_data) > 2_000_000:
                    path_id: int | str = getattr(obj, "path_id", 0)
                    file_name: str = f"I2Languages_{path_id}.dat"
                    output_path: Path = EXPORT_DIR / file_name

                    logging.info(f"✅ Found potential I2Languages ({len(raw_data)} bytes). Exporting to {output_path}")
                    with open(output_path, "wb") as f:
                        f.write(raw_data)
                    found_i2 = True

    logging.info("--- Extraction Summary ---")
    logging.info(f"Object Types found: {obj_stats}")

    if not found_weapon:
        logging.error("❌ Could not find WeaponInfo TextAsset (checked Name and Content).")

    if not found_i2:
        logging.error("❌ Could not find I2Languages MonoBehaviour.")

    logging.info("UnityPy extraction finished.")
