import logging
import subprocess
import shutil
from pathlib import Path
from .config import EXPORT_DIR, ASSET_RIPPER_DIR

def run_asset_extractions(sk_extracted_path: Path) -> None:
    """
    Sử dụng AssetRipper để export toàn bộ project, sau đó tìm file WeaponInfo và I2Languages.
    """
    # Đường dẫn file thực thi AssetRipper
    # Trên Linux là binary "AssetRipper", trên Windows là "AssetRipper.exe"
    executable = ASSET_RIPPER_DIR / "AssetRipper"
    if not executable.exists():
        executable = ASSET_RIPPER_DIR / "AssetRipper.exe"

    if not executable.exists():
        raise FileNotFoundError(f"AssetRipper binary not found at {ASSET_RIPPER_DIR}")

    # Đường dẫn output tạm thời cho AssetRipper
    # AssetRipper sẽ tạo ra cấu trúc project Unity (Assets/...)
    ripped_output = EXPORT_DIR / "RippedProject"

    # Xóa folder cũ nếu có để tránh conflict
    if ripped_output.exists():
        try:
            shutil.rmtree(ripped_output)
        except Exception as e:
            logging.warning(f"Could not clean up old ripped folder: {e}")

    ripped_output.mkdir(parents=True, exist_ok=True)

    # AssetRipper nhận input là thư mục chứa game data (thường là assets/bin/Data hoặc assets)
    # Với APK giải nén, ta trỏ vào folder assets
    game_data_path = sk_extracted_path / "assets"

    if not game_data_path.exists():
        raise FileNotFoundError(f"Game assets folder not found: {game_data_path}")

    # Command line AssetRipper:
    # ./AssetRipper <input_folder> -o <output_folder> -q (quit after finish)
    cmd = [
        str(executable),
        str(game_data_path),
        "-o", str(ripped_output),
        "-q"
    ]

    logging.info(f"Running AssetRipper on {game_data_path}...")
    logging.info("This process is resource intensive and may take 5-10 minutes. Please wait...")

    try:
        # Timeout 15 phút (900s) vì AssetRipper chạy khá lâu với project lớn
        # cwd=ASSET_RIPPER_DIR quan trọng để nó load dependencies
        subprocess.run(cmd, check=True, cwd=str(ASSET_RIPPER_DIR), timeout=900)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"AssetRipper failed with exit code {e.returncode}") from e
    except subprocess.TimeoutExpired:
        raise RuntimeError("AssetRipper timed out after 15 minutes!")

    logging.info("AssetRipper finished. Scanning output for target files...")

    # --- Tìm và Copy file WeaponInfo và I2Languages ---

    found_weapon = False
    found_i2 = False

    # Target folder export cuối cùng
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Quét đệ quy thư mục output của AssetRipper
    # Cấu trúc thường là: RippedProject/ExportedProject/Assets/...
    for file_path in ripped_output.rglob("*"):
        if not file_path.is_file():
            continue

        file_name_lower = file_path.name.lower()

        # 1. Tìm WeaponInfo
        # AssetRipper có thể export thành .txt, .json, .bytes hoặc .yaml
        if "weaponinfo" in file_name_lower:
            # Bỏ qua các file meta của Unity
            if file_path.suffix == ".meta":
                continue

            # Kiểm tra nội dung sơ bộ để chắc chắn là file JSON chứa vũ khí
            try:
                # Đọc 500 bytes đầu
                with open(file_path, "rb") as f:
                    head = f.read(500)

                # Check dấu hiệu JSON vũ khí
                if b"weapons" in head or b"forgeable" in head:
                    dest_path = EXPORT_DIR / "WeaponInfo.txt"
                    shutil.copy2(file_path, dest_path)
                    logging.info(f"✅ Found WeaponInfo at {file_path}. Copied to {dest_path}")
                    found_weapon = True
            except Exception as e:
                logging.warning(f"Error checking file {file_path}: {e}")

        # 2. Tìm I2Languages
        # I2Languages thường là file Asset lớn (MonoBehaviour)
        elif "i2languages" in file_name_lower:
            if file_path.suffix == ".meta" or "script" in file_name_lower:
                continue

            # Kiểm tra kích thước > 2MB (File I2Languages rất lớn)
            # AssetRipper export ra .asset (YAML Text) hoặc .dat (Binary) tùy version/setting
            if file_path.stat().st_size > 2_000_000:
                dest_path = EXPORT_DIR / file_path.name
                shutil.copy2(file_path, dest_path)
                logging.info(f"✅ Found potential I2Languages ({file_path.stat().st_size} bytes) at {file_path}. Copied to {dest_path}")
                found_i2 = True

    # Report lỗi nếu không tìm thấy
    if not found_weapon:
        logging.error("❌ Could not find WeaponInfo in the ripped project.")

    if not found_i2:
        logging.error("❌ Could not find I2Languages file.")

    # Cleanup: Xóa thư mục ripped nặng nề để tiết kiệm ổ cứng runner
    try:
        if ripped_output.exists():
            shutil.rmtree(ripped_output)
            logging.info("Cleaned up temporary RippedProject folder.")
    except Exception as e:
        logging.warning(f"Failed to clean up RippedProject: {e}")
