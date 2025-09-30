def plan(mapping, spaces, params):
    pos = {s["name"]: (s.get("cx", 0), s.get("cy", 0), s.get("cz", 0)) for s in spaces}
    items = []
    for z in params["zones"]:
        nm = z["name"]
        r = mapping.get(nm, nm)
        x, y, z0 = pos.get(r, (0, 0, 0))
        items.append(
            {
                "room_name": r,
                "category": "heating",
                "type": "POC_RADIATOR",
                "pos": {"x": x, "y": y, "z": z0},
                "params": {
                    "setpoint_c": float(z.get("temp_c", 22.0)),
                    "class": z.get("class"),
                    "system_type": params.get("system_type"),
                    "heat_source": params.get("heat_source"),
                    "schedule": params.get("temperature_schedule"),
                },
            }
        )
    return items
