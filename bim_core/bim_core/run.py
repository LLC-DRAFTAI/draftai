import argparse
import json
import os
import re
import sys

# Добавляем текущую папку (bim_core) в sys.path, чтобы Python видел ifc_reader.py
sys.path.append(os.path.dirname(__file__))
try:
    from ifc_reader import export_spaces
except ImportError:
    raise ImportError("ifc_reader.py not found. IFC parsing unavailable.")

from synonyms import SYNONYMS
from rapidfuzz import process


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize(s: str) -> str:
    return re.sub(r"\d+", "", s or "").strip().lower()


def parse_t_in_out(tz: dict):
    t_in = tz.get("t_in")
    t_out = tz.get("t_out")

    sched = tz.get("temperature_schedule") or tz.get("schedule")
    if not sched:
        heating = tz.get("heating_system", {})
        if isinstance(heating, dict):
            sched = heating.get("temperature")

    if (t_in is None or t_out is None) and isinstance(sched, str):
        parts = re.findall(r"\d+", sched)
        if len(parts) >= 2:
            t_in = t_in if t_in is not None else int(parts[0])
            t_out = t_out if t_out is not None else int(parts[1])

    return t_in, t_out


def build_room_specs(tz_data: dict):
    specs = []
    room_temps = tz_data.get("room_temperatures") or {}
    if isinstance(room_temps, dict):
        for k, v in room_temps.items():
            specs.append({"name": k, "temperature": float(str(v).replace(",", "."))})
    elif isinstance(room_temps, list):
        for item in room_temps:
            if isinstance(item, dict) and "name" in item:
                temperature = item.get("temperature")
                if temperature is not None:
                    temperature = float(str(temperature).replace(",", "."))
                specs.append({"name": item["name"], "temperature": temperature})

    t_in, t_out = parse_t_in_out(tz_data)
    heating = tz_data.get("heating_system", {})
    radiator_type = heating.get("radiator_type")

    for s in specs:
        s["t_in"] = t_in
        s["t_out"] = t_out
        s["radiator_type"] = radiator_type

    return specs


def find_spec_for_space(space_name: str, specs: list):
    sname = normalize(space_name)
    for spec in specs:
        base = normalize(spec["name"])
        if base and base in sname:
            return spec, spec["name"]
        syns = SYNONYMS.get(base, [])
        for syn in syns:
            if normalize(syn) and normalize(syn) in sname:
                return spec, syn
    return None, None


def suggest_match(space_name, specs):
    candidates = [spec["name"] for spec in specs]
    if not candidates:
        return None
    best = process.extractOne(space_name, candidates, score_cutoff=60)
    if best:
        return best[0]
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ifc", required=False)
    p.add_argument("--tz", required=True)
    p.add_argument("--spaces", required=False)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    # Если указан IFC, генерируем spaces.json автоматически
    if args.ifc:
        module_dir = os.path.dirname(__file__)  # папка bim_core/bim_core
        runs_dir = os.path.join(
            module_dir, "..", "runs"
        )  # bim_core/runs (или os.path.join(module_dir, "runs"))
        runs_dir = os.path.normpath(runs_dir)
        os.makedirs(runs_dir, exist_ok=True)
        spaces_file = os.path.join(runs_dir, "spaces.json")
        export_spaces(args.ifc, spaces_file)
        args.spaces = spaces_file

    if not args.spaces:
        raise ValueError("No spaces.json provided or generated from IFC.")

    tz = load_json(args.tz)
    spaces = load_json(args.spaces)
    spaces_list = spaces.get("spaces", spaces)

    specs = build_room_specs(tz)

    stubs = []
    matched = []
    unmatched_spaces = []

    for sp in spaces_list:
        spec, matched_by = find_spec_for_space(sp.get("name", ""), specs)
        if spec:
            stub = {
                "id": sp.get("id"),
                "name": spec["name"],
                "system": "heating",
                "t_in": spec.get("t_in"),
                "t_out": spec.get("t_out"),
                "temperature": spec.get("temperature"),
                "radiator_type": spec.get("radiator_type"),
                "coordinates": sp.get("coordinates", [0, 0, 0]),
            }
            stubs.append(stub)
            matched.append(
                {
                    "space": sp,
                    "tz_room": {
                        "name": spec["name"],
                        "temperature": spec.get("temperature"),
                        "t_in": spec.get("t_in"),
                        "t_out": spec.get("t_out"),
                        "radiator_type": spec.get("radiator_type"),
                    },
                    "matched_by": matched_by,
                }
            )
        else:
            suggestion = suggest_match(sp.get("name", ""), specs)
            unmatched_spaces.append(
                {
                    "id": sp.get("id"),
                    "name": sp.get("name"),
                    "suggested_match": suggestion,
                }
            )

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "stubs.json"), "w", encoding="utf-8") as f:
        json.dump(stubs, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out, "match_report.json"), "w", encoding="utf-8") as f:
        json.dump(
            {"matched": matched, "unmatched_spaces": unmatched_spaces},
            f,
            ensure_ascii=False,
            indent=2,
        )


if __name__ == "__main__":
    main()
