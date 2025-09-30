from typing import Dict, List

SYN = {
    "офис": "Офис",
    "кабинет": "Офис",
    "коридор": "Коридор",
    "вестибюль": "Коридор",
    "холл": "Коридор",
    "лестниц": "Лестница",
    "веранд": "Веранда",
}


def cls_from_name(n: str) -> str:
    s = (n or "").lower()
    for k, v in SYN.items():
        if k in s:
            return v
    return "Офис"


def build(user: Dict, space_names: List[str]) -> Dict:
    temps = {
        k.strip(): float(str(v).replace(",", "."))
        for k, v in (user.get("room_temperatures") or {}).items()
    }
    schedule = (user.get("heating_system") or {}).get("temperature") or ""
    zones = []
    for nm in space_names:
        cls = cls_from_name(nm)
        t = temps.get(cls, 22.0)
        zones.append({"name": nm, "class": cls, "temp_c": t})
    return {
        "project": user.get("project_name") or "Проект",
        "system_type": (user.get("heating_system") or {}).get("system_name")
        or "отопление",
        "heat_source": (user.get("heating_system") or {}).get("heat_source") or "",
        "temperature_schedule": schedule,
        "zones": zones,
    }
