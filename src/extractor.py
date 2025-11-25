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
    Sử dụng UnityPy để:
    1. Tìm file data.unity3d (thường chứa global managers).
    2. Extract I2Languages (dạng MonoBehaviour raw bytes).
    3. Extract WeaponInfo (dạng TextAsset).
    """
    unity_data_path = sk_extracted_path / "assets/bin/Data/data.unity3d"

    if not unity_data_path.exists():
        # Fallback: Thử tìm trong các file khác nếu cấu trúc APK thay đổi,
        # nhưng thường SK để trong data.unity3d
        raise FileNotFoundError(f"Unity data file missing: {unity_data_path}")

    logging.info(f"Loading Unity assets from: {unity_data_path}")

    # Tạo thư mục export
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Load environment
    env: Any = UnityPy.load(str(unity_data_path))

    found_i2: bool = False
    found_weapon: bool = False

    # Duyệt qua các object trong file
    obj: Any
    for obj in env.objects:

        # 1. Xử lý TextAsset (Tìm WeaponInfo)
        if obj.type.name == "TextAsset":
            data: Any = obj.read()
            if hasattr(data, 'name') and data.name == "WeaponInfo":
                output_path: Path = EXPORT_DIR / "WeaponInfo.txt"
                logging.info(f"Found WeaponInfo. Exporting to {output_path}")
                # WeaponInfo là file text/json
                if hasattr(data, 'script'):
                    script_data: bytes = data.script if isinstance(data.script, bytes) else data.script.encode('utf-8')
                    with open(output_path, "wb") as f:
                        f.write(script_data)
                    found_weapon = True

        # 2. Xử lý MonoBehaviour (Tìm I2Languages)
        elif obj.type.name == "MonoBehaviour":
            # I2Languages thường là file rất nặng (vài MB).
            # UnityPy cho phép lấy raw_data.
            # Vì MonoBehaviour không luôn có tên rõ ràng (m_Name),
            # ta dùng cách kiểm tra Script liên kết hoặc kích thước file.

            # Cách an toàn nhất với SK hiện tại: Kiểm tra Script Name nếu có,
            # hoặc đơn giản là dump hết các MB lớn ra để parser lọc sau (như cách cũ).

            # Tuy nhiên, để tối ưu, ta thử lấy script name:
            if obj.serialized_type.nodes:
                # Nếu đã parse được tree, bỏ qua vì ta cần RAW bytes cho parser.py cũ
                pass

            # Lấy data raw
            raw_data: bytes = obj.get_raw_data()

            # Filter sơ bộ: I2Languages thường > 2MB
            if len(raw_data) > 2_000_000:
                # Có thể check thêm script name nếu cần thiết, nhưng check size khá an toàn với SK
                # Để chắc chắn, ta lưu file với tên tạm, parser sẽ check kỹ header sau.

                # Lưu ý: UnityPy có thể trả về obj.path_id là unique ID
                path_id: int | str = getattr(obj, 'path_id', 0)
                file_name: str = f"I2Languages_{path_id}.dat"
                output_path: Path = EXPORT_DIR / file_name

                logging.info(f"Found potential I2Languages ({len(raw_data)} bytes). Exporting to {output_path}")
                with open(output_path, "wb") as f:
                    f.write(raw_data)
                found_i2 = True

    if not found_weapon:
        logging.warning("Could not find WeaponInfo TextAsset via UnityPy.")

    if not found_i2:
        logging.warning("Could not find any large MonoBehaviour (candidate for I2Languages).")

    logging.info("UnityPy extraction finished.")
