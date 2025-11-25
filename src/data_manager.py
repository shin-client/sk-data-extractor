import csv
import re
import logging
from pathlib import Path
from typing import Dict, Set, Optional, Any


def load_language_map(csv_path: Path, language: str = "English") -> Dict[str, str]:
    """
    Load CSV và resolve các alias như {boss18} -> boss18 -> final string.
    """
    raw_map: Dict[str, str] = {}
    resolved_map: Dict[str, str] = {}

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV path not found: {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid = row["id"].strip()
            # Fallback nếu ngôn ngữ không tồn tại trong row
            eng = row.get(language, "").strip()
            raw_map[rid] = eng

    def resolve(key: str, visited: Optional[Set[str]] = None) -> str:
        if key in resolved_map:
            return resolved_map[key]
        if visited is None:
            visited = set()
        if key in visited:
            return f"[Cyclic alias: {key}]"
        visited.add(key)

        val = raw_map.get(key, "")
        if val.startswith("{") and val.endswith("}"):
            ref = val[1:-1]
            resolved = resolve(ref, visited)
            resolved_map[key] = resolved
            return resolved
        else:
            resolved_map[key] = val
            return val

    # Resolve everything
    for k in raw_map:
        resolve(k)

    return resolved_map


def build_dictionaries(csv_path: Path) -> Dict[str, Any]:
    """
    Đọc resolved language map và build các từ điển lookup (weapons, pets...).
    """
    logging.info("Building data dictionaries from CSV...")
    lang_map = load_language_map(csv_path)

    weapons_map = {}
    buff_names = {}
    buff_infos = {}
    challenge_names = {}
    challenge_titles = {}
    challenge_descs = {}
    materials = {}
    plant_ids = {}
    pets = {}
    characters: Dict[str, Dict[str, str]] = {}

    for rid, eng in lang_map.items():
        if rid.startswith("weapon/"):
            weapons_map[rid.replace("weapon/", "")] = eng

        elif rid.startswith("Buff_name_"):
            buff_names[rid] = eng
        elif rid.startswith("Buff_info_"):
            buff_infos[rid] = eng

        elif rid.startswith("task/"):
            m = re.match(r"task/([^_]+)(_title|_desc)?", rid)
            if not m:
                continue
            cid, suffix = m.groups()
            if suffix == "_title":
                challenge_titles[cid] = eng
            elif suffix == "_desc":
                challenge_descs[cid] = eng
            else:
                challenge_names[cid] = eng

        elif rid.startswith("material_"):
            materials[rid] = eng

        elif rid.startswith("plant_") and "/" not in rid:
            plant_ids[rid] = eng

        elif (
            rid.startswith("Pet_name_")
            and not rid.endswith("_des")
            and not rid.endswith("_lock")
        ):
            pets[rid] = eng

        else:
            m = re.match(r"Character(\d+)_name_skin(\d+)", rid)
            if m:
                char_index, skin_index = m.groups()
                characters.setdefault(char_index, {})[skin_index] = eng

    return {
        "weapons": weapons_map,
        "buff_names": buff_names,
        "buff_infos": buff_infos,
        "challenge_names": challenge_names,
        "challenge_titles": challenge_titles,
        "challenge_descs": challenge_descs,
        "materials": materials,
        "plants": plant_ids,
        "pets": pets,
        "characters": characters,
    }
