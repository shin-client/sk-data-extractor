import sys
import logging

# Import các module từ src
from src import downloader, parser, exporter, utils, extractor, data_manager
from src.config import EXPORT_DIR, OUTPUT_DIR

def main() -> None:
    utils.setup_logger()
    logging.info("Starting Soul Knight Data Extraction (Ubuntu/AssetRipper Mode)")

    # --- 1. Get Info, Download & Setup ---
    try:
        version, link = downloader.get_latest_apk_info()
        logging.info(f"Latest version: {version}")

        sk_extracted_path = downloader.ensure_apk_extracted(version, link)

        # Setup AssetRipper
        downloader.ensure_asset_ripper()

    except Exception as e:
        logging.error(f"Initialization failed: {e}")
        sys.exit(1)

    # --- 2. Extract Assets ---
    try:
        logging.info("Starting AssetRipper extraction (this may take a while)...")
        extractor.run_asset_extractions(sk_extracted_path)
    except Exception as e:
        logging.error(f"Extraction failed: {e}")
        sys.exit(1)

    # --- 3. Parse Data (I2Languages) ---
    try:
        # Tìm file I2Languages
        i2_files = list(EXPORT_DIR.rglob("I2Languages*"))
        valid_i2 = None
        for f in i2_files:
            # AssetRipper có thể export ra .asset (YAML) hoặc .dat
            if f.stat().st_size >= 2_000_000:
                valid_i2 = f
                break

        if not valid_i2:
             logging.warning("No valid I2Languages file found (>= 2MB). Parsing skipped.")
             csv_path = None
        else:
            logging.info(f"Parsing I2 file: {valid_i2.name}")
            # LƯU Ý: Nếu valid_i2 là file YAML (.asset), parser này CÓ THỂ FAIL.
            try:
                records, _ = parser.parse_i2_asset_file(valid_i2)
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                csv_path = exporter.write_i2_csv(version, records)
                logging.info(f"Raw CSV exported: {csv_path}")
            except Exception as e:
                logging.error(f"Parsing I2Languages failed (File might be YAML format?): {e}")
                csv_path = None

    except Exception as e:
        logging.error(f"Parsing process failed: {e}")
        sys.exit(1)

    # --- 4. Process Data & Final Exports ---
    # Chỉ chạy nếu có CSV (tức là parse I2 thành công)
    if csv_path:
        try:
            lang_maps = data_manager.build_dictionaries(csv_path)
            full_lang_map = data_manager.load_language_map(csv_path, "English")
            full_lang_map_cn = data_manager.load_language_map(csv_path, "Chinese (Simplified)")

            # Tìm file WeaponInfo
            weapon_json_file = EXPORT_DIR / "WeaponInfo.txt"
            if not weapon_json_file.exists():
                # Thử tìm file json nếu AssetRipper đổi đuôi
                weapon_json_file = EXPORT_DIR / "WeaponInfo.json"

            if not weapon_json_file.exists():
                logging.warning("WeaponInfo.txt not found. Skipping weapon-related exports.")
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
    else:
        logging.warning("Skipping data processing because I2Languages was not parsed.")

if __name__ == "__main__":
    main()
