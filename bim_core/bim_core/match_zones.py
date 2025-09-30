from rapidfuzz import fuzz


def match(zone_names, room_names, cutoff=65):
    mapping = {}
    report = {"pairs": [], "unmatched_zones": [], "unmatched_rooms": []}
    used = set()
    for zn in zone_names:
        bs = 0
        br = None
        for rn in room_names:
            if rn in used:
                continue
            sc = fuzz.token_set_ratio(zn.lower(), rn.lower())
            if sc > bs:
                bs = sc
                br = rn
        if br and bs >= cutoff:
            mapping[zn] = br
            used.add(br)
            report["pairs"].append({"zone": zn, "room": br, "score": int(bs)})
        else:
            report["pairs"].append({"zone": zn, "room": None, "score": int(bs)})
            report["unmatched_zones"].append(zn)
    for rn in room_names:
        if rn not in used:
            report["unmatched_rooms"].append(rn)
    return mapping, report
