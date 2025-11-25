import sys
import logging
from src import downloader, parser, exporter, utils, extractor, data_manager
from src.config import EXPORT_DIR, OUTPUT_DIR

def main() -> None:
    utils.setup_logger()
    logging.info("Starting Soul Knight Data Extraction (Ubuntu/UnityPy Mode)")

    # --- 1. Get Info & Download ---
    try:
        version, link = downloader.get_latest_apk_info()
        # Chỉ cần download và extract APK
        sk_extracted_path = downloader.ensure_apk_extracted(version, link)
    except Exception as e:
        logging.error(f"Initialization failed: {e}")
        sys.exit(1)

    # --- 2. Extract Assets with UnityPy ---
    try:
        logging.info("Starting UnityPy extraction...")
        # Hàm này giờ dùng UnityPy, không cần AssetStudio path nữa
        extractor.run_asset_extractions(sk_extracted_path)
    except Exception as e:
        logging.error(f"Extraction failed: {e}")
        sys.exit(1)

    # --- 3. Parse Data (I2Languages) ---
    try:
        # (Logic giữ nguyên: tìm file .dat lớn nhất)
        i2_files = list(EXPORT_DIR.rglob("I2Languages*.dat"))
        valid_i2 = None
        for f in i2_files:
            if f.stat().st_size >= 2_000_000:
                valid_i2 = f
                break

        if not valid_i2:
            raise FileNotFoundError("No valid I2Languages .dat file found (>= 2MB)")

        logging.info(f"Parsing I2 file: {valid_i2.name}")
        records, _ = parser.parse_i2_asset_file(valid_i2)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        csv_path = exporter.write_i2_csv(version, records)
        logging.info(f"Raw CSV exported: {csv_path}")

    except Exception as e:
        logging.error(f"Parsing failed: {e}")
        sys.exit(1)

    # --- 4. Process Data ---
    try:
        lang_maps = data_manager.build_dictionaries(csv_path)
        full_lang_map = data_manager.load_language_map(csv_path, "English")
        full_lang_map_cn = data_manager.load_language_map(csv_path, "Chinese (Simplified)")
    except Exception as e:
        logging.error(f"Data processing failed: {e}")
        sys.exit(1)

    # --- 5. Final Exports ---
    try:
        weapon_json_file = None
        # UnityPy extractor đặt tên là WeaponInfo.txt, ta tìm chính xác
        possible_weapon_file = EXPORT_DIR / "WeaponInfo.txt"
        if possible_weapon_file.exists():
            weapon_json_file = possible_weapon_file

        if not weapon_json_file:
            logging.warning("WeaponInfo.txt not found. Skipping weapon exports.")
        else:
            txt_path = exporter.write_master_txt(version, weapon_json_file, lang_maps)
            logging.info(f"Master TXT exported: {txt_path}")

            exporter.export_filtered_weapons_from_info(
                weapon_json_file,
                lang_maps["weapons"],
                OUTPUT_DIR / f"weapons_{version}.json"
            )

        exporter.export_weapon_evo_data(
            full_lang_map,
            OUTPUT_DIR / f"weapon_skins_{version}.json"
        )

        exporter.export_needed_data_from_langmap(
            full_lang_map,
            OUTPUT_DIR / f"needed_data_{version}.json"
        )
        exporter.export_needed_data_from_langmap(
            full_lang_map_cn,
            OUTPUT_DIR / f"needed_data_cn_{version}.json"
        )

        logging.info("All exports completed successfully.")

    except Exception as e:
        logging.error(f"Exporting failed: {e}")
        sys.exit(1)

    # Cleanup (Optional)
    # try:
    #     if DATA_DIR.exists():
    #         shutil.rmtree(DATA_DIR)
    #         logging.info("Cleaned up temporary data.")
    # except Exception as e:
    #     logging.warning(f"Cleanup failed: {e}")

if __name__ == "__main__":
    main()
