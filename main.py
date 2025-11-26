import shutil
import sys
import logging

# Import các module từ src
from src import downloader, parser, exporter, utils, extractor, data_manager
from src.config import EXPORT_DIR, OUTPUT_DIR


def main() -> None:
    utils.setup_logger()
    logging.info("Starting Soul Knight Data Extraction (Ubuntu/AssetStudioCLI Mode)")

    # --- 1. Get Info, Download & Setup ---
    try:
        version, link = downloader.get_latest_apk_info()
        logging.info(f"Latest version: {version}")

        sk_extracted_path = downloader.ensure_apk_extracted(version, link)
        downloader.ensure_asset_studio()

    except Exception as e:
        logging.error(f"Initialization failed: {e}")
        sys.exit(1)

    # --- 2. Extract Assets ---
    try:
        logging.info("Starting AssetStudio extraction...")
        extractor.run_asset_extractions(sk_extracted_path)
    except Exception as e:
        logging.error(f"Extraction failed: {e}")
        sys.exit(1)

    # --- 3. Parse Data (I2Languages) ---
    try:
        # Tạo thư mục output theo version
        version_output_dir = OUTPUT_DIR / version
        version_output_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Output directory: {version_output_dir}")

        # Tìm file I2Languages
        i2_files = list(EXPORT_DIR.rglob("I2Languages*.dat"))
        valid_i2 = None
        for f in i2_files:
            if f.stat().st_size >= 2_000_000:
                valid_i2 = f
                break

        if not valid_i2:
            # Fallback tìm file không đuôi
            for f in EXPORT_DIR.rglob("I2Languages*"):
                if f.is_file() and f.stat().st_size >= 2_000_000 and f.suffix == "":
                    valid_i2 = f
                    break

        if not valid_i2:
            raise FileNotFoundError("No valid I2Languages .dat file found (>= 2MB)")

        logging.info(f"Parsing I2 file: {valid_i2.name}")
        records, _ = parser.parse_i2_asset_file(valid_i2)

        csv_path = exporter.write_i2_csv(version, records, version_output_dir)
        logging.info(f"Raw CSV exported: {csv_path}")

    except Exception as e:
        logging.error(f"Parsing failed: {e}")
        sys.exit(1)

    # --- 4. Process Data & Final Exports ---
    try:
        lang_maps = data_manager.build_dictionaries(csv_path)
        full_lang_map = data_manager.load_language_map(csv_path, "English")
        full_lang_map_cn = data_manager.load_language_map(
            csv_path, "Chinese (Simplified)"
        )

        # --- XỬ LÝ WEAPON FILES (Info & Item) ---
        weapon_info_file = None
        weapon_item_file = None

        # 1. Quét thư mục MỘT LẦN duy nhất để tìm các file cần thiết
        for f in EXPORT_DIR.iterdir():
            name_lower = f.name.lower()

            if "weaponinfo" in name_lower and f.suffix == ".txt":
                weapon_info_file = f
            elif "weaponitem" in name_lower and f.suffix == ".txt":
                weapon_item_file = f

        # 2. Xử lý WeaponInfo (Parse & Export JSON)
        if not weapon_info_file:
            logging.warning("WeaponInfo.txt not found. Skipping weapon exports.")
        else:
            exporter.export_master_data_to_json(
                version, weapon_info_file, lang_maps, version_output_dir
            )
            logging.info("Master data exported to multiple JSON files.")

            exporter.export_filtered_weapons_from_info(
                weapon_info_file,
                lang_maps["weapons"],
                version_output_dir / "weapons.json",
            )

        # 3. Xử lý WeaponItem
        if not weapon_item_file:
            logging.warning("WeaponItem file not found in export directory.")
        else:
            dest_path = version_output_dir / "weapon_items.json"

            shutil.copy2(weapon_item_file, dest_path)
            logging.info(f"Copied and renamed WeaponItem to: {dest_path}")

        exporter.export_weapon_evo_data(
            full_lang_map, version_output_dir / "weapon_skins.json"
        )
        exporter.export_needed_data_from_langmap(
            full_lang_map, version_output_dir / "needed_data.json"
        )
        exporter.export_needed_data_from_langmap(
            full_lang_map_cn, version_output_dir / "needed_data_cn.json"
        )

        logging.info("All exports completed successfully.")

    except Exception as e:
        logging.error(f"Exporting failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
