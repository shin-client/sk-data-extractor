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
    Sử dụng UnityPy với cơ chế quét file mạnh mẽ hơn để tìm I2Languages và WeaponInfo.
    """
    # 1. Tìm tất cả các file có thể chứa asset trong thư mục assets
    # Soul Knight thường để ở assets/bin/Data, nhưng ta quét rộng hơn để chắc chắn
    assets_root: Path = sk_extracted_path / "assets"
    
    # Tìm các file có đuôi phổ biến hoặc file quan trọng không đuôi (như globalgamemanagers)
    files_to_load: list[Path] = []
    
    # Các pattern file Unity thường gặp
    patterns: list[str] = ["*.assets", "*.unity3d", "*.resource", "*.bundle", "globalgamemanagers", "data.unity3d"]
    
    if assets_root.exists():
        for pattern in patterns:
            files_to_load.extend(list(assets_root.rglob(pattern)))
        
        # Thêm trường hợp file resources không có đuôi (đôi khi xảy ra)
        potential_resources: list[Path] = list(assets_root.rglob("resources"))
        files_to_load.extend(potential_resources)
    else:
        raise FileNotFoundError(f"Assets directory missing: {assets_root}")

    # Loại bỏ trùng lặp và convert sang string
    files_to_load_str: list[str] = list(set([str(p) for p in files_to_load]))
    
    if not files_to_load_str:
        raise RuntimeError("No Unity asset files found in the extracted APK!")

    logging.info(f"Loading {len(files_to_load_str)} asset files via UnityPy...")
    # In ra 5 file đầu tiên để debug
    for f in files_to_load_str[:5]:
        logging.info(f" - Loading: {Path(f).name}")

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load tất cả file tìm được
    env: Any = UnityPy.load(*files_to_load_str)
    
    found_i2: bool = False
    found_weapon: bool = False
    
    # Thống kê object để debug
    obj_stats: dict[str, int] = {}

    # Duyệt qua các object
    obj: Any
    for obj in env.objects:
        
        # Thống kê type
        type_str: str = str(obj.type.name) if hasattr(obj, "type") else "Unknown"
        obj_stats[type_str] = obj_stats.get(type_str, 0) + 1

        # --- 1. Xử lý TextAsset (ClassID 49) ---
        if obj.type.name == "TextAsset":
            data: Any = obj.read()
            if hasattr(data, "name") and data.name == "WeaponInfo":
                output_path: Path = EXPORT_DIR / "WeaponInfo.txt"
                logging.info(f"✅ Found WeaponInfo! Exporting to {output_path}")
                if hasattr(data, "script"):
                    script_data: bytes = (
                        data.script
                        if isinstance(data.script, bytes)
                        else data.script.encode("utf-8")
                    )
                    with open(output_path, "wb") as f:
                        f.write(script_data)
                    found_weapon = True
            
            # Debug: In thử tên vài text asset nếu chưa tìm thấy WeaponInfo
            if not found_weapon and obj_stats["TextAsset"] <= 5:
                asset_name: str = data.name if hasattr(data, "name") else "Unknown"
                logging.info(f"   (Seen TextAsset: {asset_name})")

        # --- 2. Xử lý MonoBehaviour (ClassID 114) - Tìm I2Languages ---
        elif obj.type.name == "MonoBehaviour":
            # I2Languages thường rất nặng (> 2MB)
            byte_size: int = getattr(obj, "byte_size", 0)
            if byte_size > 2_000_000:
                raw_data: bytes = obj.get_raw_data()
                if len(raw_data) > 2_000_000:
                    # Đặt tên file có path_id để tránh trùng
                    path_id: int | str = getattr(obj, "path_id", 0)
                    file_name: str = f"I2Languages_{path_id}.dat"
                    output_path: Path = EXPORT_DIR / file_name
                    
                    logging.info(f"✅ Found potential I2Languages ({len(raw_data)} bytes). Exporting to {output_path}")
                    with open(output_path, "wb") as f:
                        f.write(raw_data)
                    found_i2 = True

    # Report kết quả
    logging.info("--- Extraction Summary ---")
    logging.info(f"Object Types found: {obj_stats}")
    
    if not found_weapon:
        logging.error("❌ Could not find WeaponInfo TextAsset.")
        # Nếu có TextAsset nhưng không phải WeaponInfo, lỗi do tên file đổi hoặc file nằm chỗ khác
        if obj_stats.get("TextAsset", 0) > 0:
            logging.warning("TextAssets were found, but none named 'WeaponInfo'. Check log for list.")
        else:
            logging.warning("No TextAssets found at all. 'resources.assets' might not be loaded.")
    
    if not found_i2:
        logging.error("❌ Could not find I2Languages MonoBehaviour.")

    logging.info("UnityPy extraction finished.")
