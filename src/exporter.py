import json
import csv
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import List, Tuple, Dict, Any, Union
from .config import LANGUAGES


def write_i2_csv(
    version: str, records: List[Tuple[str, List[str]]], output_dir: Path
) -> Path:
    """
    Given (key, [fields...]) records, write them into I2language_{version}.csv
    under the script folder. Returns the CSV path.
    """
    csv_path = output_dir / f"I2language.csv"
    logging.info(f"Writing CSV: {csv_path}")
    try:
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id"] + LANGUAGES)
            for key, fields in records:
                writer.writerow([key] + fields)
    except Exception as e:
        raise RuntimeError(f"Failed writing CSV {csv_path}: {e}") from e
    return csv_path


def write_master_txt(
    version: str,
    weapon_json_path: Path,
    lang_maps: Dict[str, Dict[str, Any]],
    output_dir: Path,
) -> Path:
    """
    Read WeaponInfo.txt (JSON), sort weapons, then write out the big ASCII master file.
    Returns path to the TXT.
    """
    txt_path = output_dir / f"Allinfo.txt"
    logging.info(f"Writing master TXT: {txt_path}")
    if not weapon_json_path.exists():
        raise FileNotFoundError(f"WeaponInfo JSON not found: {weapon_json_path}")

    try:
        with open(weapon_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in {weapon_json_path}: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Failed reading {weapon_json_path}: {e}") from e

    weapons = data.get("weapons", [])
    weapons_sorted = sorted(weapons, key=lambda w: w.get("name", ""))

    weapons_map = lang_maps["weapons"]
    buff_names = lang_maps["buff_names"]
    buff_infos = lang_maps["buff_infos"]
    challenge_names = lang_maps["challenge_names"]
    challenge_titles = lang_maps["challenge_titles"]
    challenge_descs = lang_maps["challenge_descs"]
    materials = lang_maps["materials"]
    plants = lang_maps["plants"]
    pets = lang_maps["pets"]
    characters = lang_maps["characters"]
    max_skin_ids = {}
    try:
        with open(txt_path, "w", encoding="utf-8") as out:

            out.write(
                "██     ██ ███████  █████  ██████   ██████  ███    ██\n"
                "██     ██ ██      ██   ██ ██   ██ ██    ██ ████   ██\n"
                "██  █  ██ █████   ███████ ██████  ██    ██ ██ ██  ██\n"
                "██ ███ ██ ██      ██   ██ ██      ██    ██ ██  ██ ██\n"
                " ███ ███  ███████ ██   ██ ██       ██████  ██   ████\n\n"
            )
            for w in weapons_sorted:
                name_key = w.get("name", "")
                english_name = weapons_map.get(name_key, "[Name Not Found]")
                out.write(f"{name_key}\n")
                out.write(f"    Name      : {english_name}\n")
                out.write(f"    Forgeable : {w.get('forgeable', False)}\n")
                out.write(f"    Is melee  : {w.get('isMelle', False)}\n")
                out.write(f"    Rarity    : {w.get('level', '')}\n")
                out.write(f"    Type      : {w.get('type', '')}\n\n")

            out.write(
                " ██████ ██   ██  █████  ██████   █████   ██████ ████████ ███████ ██████\n"
                "██      ██   ██ ██   ██ ██   ██ ██   ██ ██         ██    ██      ██   ██\n"
                "██      ███████ ███████ ██████  ███████ ██         ██    █████   ██████\n"
                "██      ██   ██ ██   ██ ██   ██ ██   ██ ██         ██    ██      ██   ██\n"
                " ██████ ██   ██ ██   ██ ██   ██ ██   ██  ██████    ██    ███████ ██   ██\n\n"
            )
            for char_index in sorted(characters.keys()):
                skins = characters[char_index]
                default_name = skins.get("0", "[Unknown]")
                out.write(f"c{char_index} = {default_name}\n")
                max_skin_id = max(int(sid) for sid in skins.keys())
                max_skin_ids[f"c{char_index}"] = max_skin_id
                for skin_index in sorted(skins.keys(), key=lambda x: int(x)):
                    skin_name = skins[skin_index]
                    out.write(f"    c{char_index}_skin{skin_index} = {skin_name}\n")
                out.write("\n")

            out.write(
                "██████  ███████ ████████\n"
                "██   ██ ██         ██   \n"
                "██████  █████      ██   \n"
                "██      ██         ██   \n"
                "██      ███████    ██   \n\n"
            )
            for pet_id, pet_name in sorted(pets.items(), key=lambda kv: kv[0]):
                out.write(f"{pet_id.removeprefix('Pet_name_')}\n")
                out.write(f"    Display name : {pet_name}\n\n")

            out.write(
                "██████  ██    ██ ███████ ███████ \n"
                "██   ██ ██    ██ ██      ██      \n"
                "██████  ██    ██ █████   █████   \n"
                "██   ██ ██    ██ ██      ██      \n"
                "██████   ██████  ██      ██      \n\n"
            )
            buff_ids: set[str] = set()
            buff_ids.update(k.replace("Buff_name_", "") for k in buff_names.keys())
            buff_ids.update(k.replace("Buff_info_", "") for k in buff_infos.keys())
            for bid in sorted(buff_ids):
                name_key = f"Buff_name_{bid}"
                info_key = f"Buff_info_{bid}"
                bname = buff_names.get(name_key, "[Name Not Found]")
                binfo = buff_infos.get(info_key, "[Description Not Found]")
                out.write(f"{bid}\n")
                out.write(f"    Name        : {bname}\n")
                out.write(f"    Description : {binfo}\n\n")

            out.write(
                " ██████ ██   ██  █████  ██       █████  ███    ██  ██████  ███████ \n"
                "██      ██   ██ ██   ██ ██      ██   ██ ████   ██ ██       ██      \n"
                "██      ███████ ███████ ██      ███████ ██ ██  ██ ██   ███ █████   \n"
                "██      ██   ██ ██   ██ ██      ██   ██ ██  ██ ██ ██    ██ ██      \n"
                " ██████ ██   ██ ██   ██ ███████ ██   ██ ██   ████  ██████  ███████ \n\n"
            )
            challenge_ids: set[str] = set()
            challenge_ids.update(challenge_names.keys())
            challenge_ids.update(challenge_titles.keys())
            challenge_ids.update(challenge_descs.keys())

            for cid in sorted(
                challenge_ids, key=lambda x: int(x) if x.isdigit() else x
            ):
                name = challenge_names.get(cid, "[Name Not Found]")
                title = challenge_titles.get(cid, "[Title Not Found]")
                desc = challenge_descs.get(cid, "[Description Not Found]")
                out.write(f"{cid.removeprefix('name/')}\n")
                out.write(f"    Name        : {name}\n")
                out.write(f"    Title       : {title}\n")
                out.write(f"    Description : {desc}\n\n")

            out.write(
                "███    ███  █████  ████████ ███████ ██████  ██  █████  ██      \n"
                "████  ████ ██   ██    ██    ██      ██   ██ ██ ██   ██ ██      \n"
                "██ ████ ██ ███████    ██    █████   ██████  ██ ███████ ██      \n"
                "██  ██  ██ ██   ██    ██    ██      ██   ██ ██ ██   ██ ██      \n"
                "██      ██ ██   ██    ██    ███████ ██   ██ ██ ██   ██ ███████ \n\n"
            )
            for mid, mname in sorted(materials.items(), key=lambda kv: kv[0]):
                out.write(f"{mid}\n")
                out.write(f"    Display name : {mname}\n\n")

            out.write(
                "██████  ██       █████  ███    ██ ████████ \n"
                "██   ██ ██      ██   ██ ████   ██    ██    \n"
                "██████  ██      ███████ ██ ██  ██    ██    \n"
                "██      ██      ██   ██ ██  ██ ██    ██    \n"
                "██      ███████ ██   ██ ██   ████    ██    \n\n"
            )
            for pid, pname in sorted(plants.items(), key=lambda kv: kv[0]):
                out.write(f"{pid}\n")
                out.write(f"    Display name : {pname}\n\n")
            skin_id_json_path = output_dir / "highest_skin_ids.json"
            with open(skin_id_json_path, "w", encoding="utf-8") as f:
                json.dump(max_skin_ids, f, indent=2, sort_keys=True)
            logging.info(f"Exported max skin IDs to {skin_id_json_path}")
    except Exception as e:
        raise RuntimeError(f"Failed writing master TXT {txt_path}: {e}") from e

    return txt_path


def export_master_data_to_json(
    version: str,
    weapon_json_path: Path,
    lang_maps: Dict[str, Dict[str, Any]],
    output_dir: Path,
) -> None:
    """
    Đọc WeaponInfo.txt (JSON), kết hợp với lang_maps và xuất ra các file JSON riêng biệt
    cho: Vũ khí, Nhân vật, Thú cưng, Buff, Thử thách, Nguyên liệu, Cây trồng.
    """
    logging.info(f"Starting export to JSON files in: {output_dir}")

    if not weapon_json_path.exists():
        raise FileNotFoundError(f"WeaponInfo JSON not found: {weapon_json_path}")

    try:
        with open(weapon_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed reading {weapon_json_path}: {e}") from e

    # Lấy dữ liệu từ lang_maps
    weapons_map = lang_maps["weapons"]
    buff_names = lang_maps["buff_names"]
    buff_infos = lang_maps["buff_infos"]
    challenge_names = lang_maps["challenge_names"]
    challenge_titles = lang_maps["challenge_titles"]
    challenge_descs = lang_maps["challenge_descs"]
    materials = lang_maps["materials"]
    plants = lang_maps["plants"]
    pets = lang_maps["pets"]
    characters = lang_maps["characters"]

    # 1. Export Weapons (Kết hợp thông số gốc + tên tiếng Anh)
    weapons_raw = data.get("weapons", [])
    weapons_export = []
    for w in weapons_raw:
        name_key = w.get("name", "")
        english_name = weapons_map.get(name_key, None)

        # Chỉ lấy những trường quan trọng, thêm trường english_name
        weapon_entry = {
            "id": name_key,
            "english_name": english_name,
            "forgeable": w.get("forgeable", False),
            "is_melee": w.get("isMelle", False),
            "rarity": w.get("level", ""),
            "type": w.get("type", ""),
        }
        weapons_export.append(weapon_entry)

    # Sắp xếp theo ID
    weapons_export.sort(key=lambda x: x["id"])
    _save_json(output_dir / "all_weapons_info.json", weapons_export)

    # 2. Export Characters & Skins
    # Cấu trúc: { "c1": { "default_name": "...", "skins": { "skin_id": "name" } } }
    chars_export = {}
    max_skin_ids = {}

    for char_index in sorted(characters.keys()):
        skins = characters[char_index]
        default_name = skins.get("0", "[Unknown]")

        # Tính max skin id
        max_skin_id = 0
        skin_list = {}
        if skins:
            max_skin_id = max(int(sid) for sid in skins.keys())
            for skin_index in sorted(skins.keys(), key=lambda x: int(x)):
                skin_list[skin_index] = skins[skin_index]

        key = f"c{char_index}"
        max_skin_ids[key] = max_skin_id
        chars_export[key] = {"default_name": default_name, "skins": skin_list}

    _save_json(output_dir / "characters_info.json", chars_export)
    _save_json(output_dir / "highest_skin_ids.json", max_skin_ids)

    # 3. Export Pets
    pets_export = []
    for pet_id, pet_name in sorted(pets.items(), key=lambda kv: kv[0]):
        pets_export.append(
            {
                "id": pet_id.removeprefix("Pet_name_"),
                "full_key": pet_id,
                "name": pet_name,
            }
        )
    _save_json(output_dir / "pets_info.json", pets_export)

    # 4. Export Buffs
    buffs_export = []
    buff_ids: set[str] = set()
    buff_ids.update(k.replace("Buff_name_", "") for k in buff_names.keys())
    buff_ids.update(k.replace("Buff_info_", "") for k in buff_infos.keys())

    for bid in sorted(buff_ids):
        name_key = f"Buff_name_{bid}"
        info_key = f"Buff_info_{bid}"
        buffs_export.append(
            {
                "id": bid,
                "name": buff_names.get(name_key, "[Name Not Found]"),
                "description": buff_infos.get(info_key, "[Description Not Found]"),
            }
        )
    _save_json(output_dir / "buffs_info.json", buffs_export)

    # 5. Export Challenges
    challenges_export = []
    challenge_ids: set[str] = set()
    challenge_ids.update(challenge_names.keys())
    challenge_ids.update(challenge_titles.keys())
    challenge_ids.update(challenge_descs.keys())

    sorted_cids = sorted(challenge_ids, key=lambda x: int(x) if x.isdigit() else x)
    for cid in sorted_cids:
        challenges_export.append(
            {
                "id": cid.removeprefix(
                    "name/"
                ),  # Xử lý trường hợp id có prefix lạ nếu có
                "raw_id": cid,
                "name": challenge_names.get(cid, None),
                "title": challenge_titles.get(cid, None),
                "description": challenge_descs.get(cid, None),
            }
        )
    _save_json(output_dir / "challenges_info.json", challenges_export)

    # 6. Export Materials
    materials_export = []
    for mid, mname in sorted(materials.items(), key=lambda kv: kv[0]):
        materials_export.append({"id": mid, "name": mname})
    _save_json(output_dir / "materials_info.json", materials_export)

    # 7. Export Plants
    plants_export = []
    for pid, pname in sorted(plants.items(), key=lambda kv: kv[0]):
        plants_export.append({"id": pid, "name": pname})
    _save_json(output_dir / "plants_info.json", plants_export)

    logging.info("Exported all master data to separate JSON files.")


def _save_json(path: Path, data: Any) -> None:
    """Helper để lưu file JSON format đẹp."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Failed to save JSON {path}: {e}")


def export_filtered_weapons_from_info(
    weapon_info_path: Path,
    weapons_map: Dict[str, str],
    output_path: Path,
) -> None:
    logging.info(f"Exporting filtered weapons to {output_path}")
    try:
        with open(weapon_info_path, "r", encoding="utf-8") as f:
            info_data = json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed reading WeaponInfo.txt: {e}") from e

    weapon_list = info_data.get("weapons", [])
    ids_from_info = {w.get("name", "") for w in weapon_list if "name" in w}

    exclude_patterns = [
        re.compile(r"^weapon_000.*xx\d*$"),
        re.compile(r"^weapon_init.*xx\d*$"),
        re.compile(r"^transform_weapon_.*"),
    ]

    filtered = {}
    for wid in ids_from_info:
        if any(p.match(wid) for p in exclude_patterns):
            continue
        english_name = weapons_map.get(wid)
        if english_name:
            filtered[wid] = english_name

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2, sort_keys=True)


def export_weapon_evo_data(lang_map: Dict[str, str], output_path: Path) -> None:
    logging.info(f"Exporting weapon evo data to {output_path}")
    skin_pattern = re.compile(r"^(weapon_\w+)_s_\d+$")
    upgrade_pattern = re.compile(r"^desc_evolution_(weapon_\w+)$")

    weapon_skin_map: defaultdict[str, List[str]] = defaultdict(list)
    upgradable_weapons: set[str] = set()

    for key in lang_map:
        if "/" in key:
            continue

        m_skin = skin_pattern.match(key)
        if m_skin:
            base_weapon = m_skin.group(1)
            weapon_skin_map[base_weapon].append(key)
            continue

        m_upgrade = upgrade_pattern.match(key)
        if m_upgrade:
            weapon_id = m_upgrade.group(1)
            upgradable_weapons.add(weapon_id)
            continue

    for k, v in weapon_skin_map.items():
        weapon_skin_map[k] = sorted(v)
    upgradable_weapon_list = sorted(upgradable_weapons)

    weapon_evo_data: Dict[
        str,
        Union[int, List[str], str, Dict[str, Dict[str, Union[str, int, List[str]]]]],
    ] = {
        "blindBoxOpenCount0": 0,
        "favorWeapons": [],
        "lastOpenMachineHistoryStr0": "",
        "weapons": {
            weapon: {
                "Name": weapon,
                "Level": 1 if weapon in upgradable_weapon_list else 0,
                "CurrentSkinIndex": 1 if (skins := weapon_skin_map.get(weapon)) else 0,
                "UnlockedSkins": skins or [],
            }
            for weapon in weapon_skin_map.keys() | upgradable_weapons
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(weapon_evo_data, f, indent=2, ensure_ascii=False, sort_keys=True)


def export_needed_data_from_langmap(
    lang_map: Dict[str, str], output_path: Path
) -> None:
    logging.info(f"Exporting needed data to {output_path}")
    result: Dict[str, Any] = {
        "skin": defaultdict(dict),
        "pet": {},
        "material": {},
        "character_skill": {},
    }

    skin_pattern = re.compile(r"Character(\d+)_name_skin(\d+)")
    pet_pattern = re.compile(r"Pet_name_(\d+)")
    material_pattern = re.compile(
        r"(^material_(?!.*(?:activity|book|fragment|tape|skill|new|money|multi|box)).*)"
    )
    skill_pattern = re.compile(r"(Character\d+_skill_\d+_name)")

    for key, value in lang_map.items():
        if m := skin_pattern.fullmatch(key):
            char_idx, skin_idx = m.groups()
            result["skin"][f"c{char_idx}"][f"c{char_idx}_skin{skin_idx}"] = value
        elif m := pet_pattern.fullmatch(key):
            result["pet"][m.group(1)] = value
        elif m := material_pattern.fullmatch(key):
            result["material"][m.group(1)] = value
        elif m := skill_pattern.fullmatch(key):
            result["character_skill"][m.group(1)] = value

    result["skin"] = dict(result["skin"])
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, sort_keys=True)
