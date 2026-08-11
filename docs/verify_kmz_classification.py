"""Faithful port of AssetClassifier + KmzGeoJsonConverter, run against the real KMZ.

Mirrors the Java implementation rule-for-rule so the rule table can be validated before the
Java build is available. Any divergence here is a bug in the Java too.
"""
import re
import sys
import collections
import xml.etree.ElementTree as ET

FLAGS = re.IGNORECASE

WTG_FOLDER = ["turbine", "wtg", "wec", "approved", "proposed", "registration",
              "low aep", "cancel", "shifting", "micrositing", "micro siting"]
TOWER_FOLDER = ["gantry", "tower", "angle point", "evacuation", "transmission", "ht line", "ehv"]
SUB_FOLDER = ["pss", "substation", "s/s", "switchyard", "pgcil", "ctu"]
SURVEY_FOLDER = ["borehole", "geotech", "soil investigation", "survey point"]

WTG_ID = re.compile(r"^(KS|SUR|VAJ)[\s_-]*\d+", FLAGS)
TOWER_ID = re.compile(r"^(\d+\s*/\s*\d+|AP[\s_-]*\d+|GANTRY|TOWER[\s_-]*\d+)$", FLAGS)
SUB_ID = re.compile(r"(\bPSS\b|SUBSTATION|\bS/S\b|SWITCHYARD|\d+\s*/\s*\d+\s*KV)", FLAGS)
SURVEY_ID = re.compile(r"^(BH|CBR|ERT|PLT|TP|TRT)[\s_-]*\d+$", FLAGS)

STATUS_RULES = [("cancel location", "CANCELLED"), ("to be shifting", "TO_BE_SHIFTED"),
                ("low aep", "LOW_AEP"), ("registration", "REGISTRATION"),
                ("approved", "APPROVED"), ("proposed", "PROPOSED"),
                ("shifting", "TO_BE_SHIFTED"), ("cancel", "CANCELLED")]
OPTIMISABLE = {"APPROVED", "REGISTRATION", "PROPOSED"}

IGNORED_SEGMENTS = {"my places", "nom du document", "sheet1", "document", "folder",
                    "line features", "untitled"}
PATH_SEPARATOR = re.compile(r"\s+/\s+")


def segments_leaf_first(path):
    if not path:
        return []
    out = []
    for part in reversed(PATH_SEPARATOR.split(path)):
        seg = part.strip()
        if seg and seg.lower() not in IGNORED_SEGMENTS:
            out.append(seg)
    return out


def contains_any(hay, needles):
    return any(n in hay for n in needles)


def status_for(asset_type, segments):
    if asset_type != "WTG":
        return "UNKNOWN"
    for seg in segments:
        low = seg.lower()
        for keyword, status in STATUS_RULES:
            if keyword in low:
                return status
    return "UNKNOWN"


def classify(external_id, folder_path):
    ident = (external_id or "").strip()
    segments = segments_leaf_first(folder_path)

    for seg in segments:
        low = seg.lower()
        if contains_any(low, SURVEY_FOLDER):
            return "SURVEY_POINT", status_for("SURVEY_POINT", segments), "KML_FOLDER", seg
        if contains_any(low, TOWER_FOLDER):
            return "EVACUATION_TOWER", "UNKNOWN", "KML_FOLDER", seg
        if contains_any(low, SUB_FOLDER):
            return "SUBSTATION", "UNKNOWN", "KML_FOLDER", seg
        if contains_any(low, WTG_FOLDER):
            return "WTG", status_for("WTG", segments), "KML_FOLDER", seg

    if ident:
        if SURVEY_ID.search(ident):
            return "SURVEY_POINT", "UNKNOWN", "ID_PATTERN", ident
        if TOWER_ID.search(ident):
            return "EVACUATION_TOWER", "UNKNOWN", "ID_PATTERN", ident
        if SUB_ID.search(ident):
            return "SUBSTATION", "UNKNOWN", "ID_PATTERN", ident
        if WTG_ID.search(ident):
            return "WTG", status_for("WTG", segments), "ID_PATTERN", ident

    return "UNKNOWN", "UNKNOWN", "UNRESOLVED", ident


def normalise(i):
    return re.sub(r"[\s_\-.]", "", (i or "").upper())


def local(e):
    return e.tag.split("}")[-1]


def convert(kml_path):
    """Port of KmzGeoJsonConverter.convert - folder-aware walk with deduplication."""
    root = ET.parse(kml_path).getroot()
    features, seen = [], set()
    stats = collections.Counter()
    skipped = collections.Counter()

    def first_desc(elem, name):
        for g in elem.iter():
            if local(g) == name and g is not elem:
                return g
        return None

    def direct_child_text(elem, name):
        for c in elem:
            if local(c) == name:
                return c.text
        return None

    def walk(elem, path):
        for child in elem:
            name = local(child)
            if name in ("Folder", "Document"):
                folder_name = direct_child_text(child, "name")
                pushed = bool(folder_name and folder_name.strip())
                if pushed:
                    path.append(folder_name.strip())
                walk(child, path)
                if pushed:
                    path.pop()
            elif name == "Placemark":
                stats["total"] += 1
                point = first_desc(child, "Point")
                if point is None:
                    for g in ("LineString", "Polygon", "MultiGeometry"):
                        if first_desc(child, g) is not None:
                            skipped[g] += 1
                            break
                    else:
                        skipped["None"] += 1
                    continue
                coord = first_desc(point, "coordinates")
                if coord is None or not coord.text:
                    continue
                lon, lat = [float(v) for v in coord.text.strip().split()[0].split(",")[:2]]
                stats["points"] += 1

                nm = first_desc(child, "name")
                ext = (nm.text or "").strip() if nm is not None and nm.text else ""
                folder_path = " / ".join(path)

                key = f"{normalise(ext)}@{lon:.7f},{lat:.7f}"
                if key in seen:
                    stats["duplicates"] += 1
                    continue
                seen.add(key)
                features.append((ext, path[-1] if path else None, folder_path, lon, lat))
            else:
                walk(child, path)

    walk(root, [])
    return features, stats, skipped


def main(kml_path):
    features, stats, skipped = convert(kml_path)

    print(f"Placemarks total      : {stats['total']}")
    print(f"  Point placemarks    : {stats['points']}")
    print(f"  Duplicates removed  : {stats['duplicates']}")
    print(f"  Unique imported     : {len(features)}")
    print(f"  Skipped non-Point   : {dict(skipped)}")
    print()

    counts = collections.Counter()
    statuses = collections.Counter()
    unknowns = []
    by_type = collections.defaultdict(list)

    for ext, leaf, path, lon, lat in features:
        asset_type, status, rule, evidence = classify(ext, path)
        counts[asset_type] += 1
        by_type[asset_type].append((ext, leaf, rule))
        if asset_type == "WTG":
            statuses[status] += 1
        if asset_type == "UNKNOWN":
            unknowns.append((ext, leaf))

    print("=== Classification ===")
    for t, c in counts.most_common():
        print(f"  {t:18s} {c:4d}")
    print()
    print("=== Turbine status (folder-derived) ===")
    optimisable = 0
    for s, c in statuses.most_common():
        flag = "-> optimiser" if s in OPTIMISABLE else "   excluded"
        if s in OPTIMISABLE:
            optimisable += c
        print(f"  {s:15s} {c:4d}  {flag}")
    print(f"  {'':15s} ----")
    print(f"  optimisable      {optimisable}")
    print()
    print("=== Sample per type ===")
    for t in ("WTG", "EVACUATION_TOWER", "SUBSTATION", "SURVEY_POINT"):
        sample = by_type[t][:6]
        print(f"  {t}: {[s[0] for s in sample]}")
    print()
    print(f"=== Unresolved ({len(unknowns)}) - require a human decision, not a silent WTG ===")
    for ext, leaf in unknowns:
        print(f"  {ext!r:45s} folder={leaf!r}")

    # Assertions that must hold for the fix to be correct.
    failures = []
    if counts["EVACUATION_TOWER"] != 174:
        failures.append(f"expected 174 towers, got {counts['EVACUATION_TOWER']}")
    if counts["SURVEY_POINT"] != 15:
        failures.append(f"expected 15 survey points, got {counts['SURVEY_POINT']}")
    tower_names = {s[0] for s in by_type["EVACUATION_TOWER"]}
    if any(n.upper().startswith("KS") for n in tower_names):
        failures.append("a KS-prefixed turbine leaked into the tower set")
    wtg_names = {s[0] for s in by_type["WTG"]}
    if any(re.match(r"^\d+\s*/\s*\d+$", n) or n == "GANTRY" for n in wtg_names):
        failures.append("a tower leaked into the WTG set")
    if any(n.upper().startswith(("BH-", "CBR-", "ERT-")) for n in wtg_names):
        failures.append("a borehole leaked into the WTG set")

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("PASS: no turbine/tower/borehole cross-contamination; counts match the source file.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
