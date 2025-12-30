#!/usr/bin/env -S uv --quiet run --script
from collections import defaultdict
from pathlib import Path
from models import Zone, Access, ZoneAccessRelationship, ZoneLineRelationship, Line
from pydantic import TypeAdapter
import requests
import xml.etree.ElementTree as ET
from collections import Counter
import re
    

SOURCE = Path("./source")
GENERATED = Path("./generated/")
GENERATED_ICONS = GENERATED / "icons/"


def extract_dominant_color_from_svg(svg_path: Path) -> str:
    tree = ET.parse(svg_path)
    root = tree.getroot()
    colors = []
    # Find all fill attributes
    for elem in root.iter():
        # Check fill attribute
        fill = elem.get("fill")
        if fill and fill != "none" and fill.startswith('#') and fill.lower() != "#ffffff":
            colors.append(fill.lower())
        # Check style attribute
        style = elem.get("style")
        if style:
            fill_match = re.search(r"fill:\s*(#[0-9A-Fa-f]{6})", style)
            if fill_match and fill_match.group(1).lower() != "#ffffff":
                colors.append(fill_match.group(1).lower())
    # Get most common color
    if not colors:
        raise ValueError(f"No dominant color found in {svg_path}")
    most_common = Counter(colors).most_common(1)[0][0]
    return most_common


def clean_transformations():
    for p in GENERATED_ICONS.glob("*"):
        p.unlink()
    for p in GENERATED.glob("*.json"):
        p.unlink()


def transform_zones():
    ta = TypeAdapter(list[Zone])
    with open(SOURCE / "zones-d-arrets.json", "r") as f:
        zones = ta.validate_json(f.read())
    with open(GENERATED / "zones.json", "w") as f:
        f.write(ta.dump_json(zones, indent=4).decode())


def tranform_access():
    ta = TypeAdapter(list[Access])
    with open(SOURCE / "acces.json", "r") as f:
        accesses = ta.validate_json(f.read())
    with open(GENERATED / "accesses.json", "w") as f:
        f.write(ta.dump_json(accesses, indent=4).decode())


def transform_zone_access_relationships():
    ta = TypeAdapter(list[ZoneAccessRelationship])
    with open(SOURCE / "relations-acces.json", "r") as f:
        accesses_relationships = ta.validate_json(f.read())
    with open(GENERATED / "zones_accesses_rel.json", "w") as f:
        f.write(ta.dump_json(accesses_relationships, indent=4).decode())


def transform_zone_line_relationships():
    ta = TypeAdapter(list[ZoneLineRelationship])
    with open(SOURCE / "emplacement-des-gares-idf.json", "r") as f:
        line_relationships = ta.validate_json(f.read())
    with open(GENERATED / "zones_lines_rel.json", "w") as f:
        f.write(ta.dump_json(line_relationships, indent=4).decode())


def extract_lines():
    with open(GENERATED / "zones_lines_rel.json", "r") as f:
        ta = TypeAdapter(list[ZoneLineRelationship])
        line_relationships = ta.validate_json(f.read())
    lines_set = {
        Line(id=relationship.line_id, name=relationship.line_name, icon_url=relationship.line_icon_url, icon_filename=relationship.line_icon_filename)
        for relationship in line_relationships
    }
    lines = sorted(list(lines_set), key=lambda line: line.name)
    for line in lines:
        if line.icon_url and line.icon_filename:
            img_data = requests.get(line.icon_url).content
            with open(GENERATED_ICONS / line.icon_filename, 'wb') as f:
                f.write(img_data)
            line.color = extract_dominant_color_from_svg(GENERATED_ICONS / line.icon_filename)

    with open(GENERATED / "lines.json", "w") as f:
        ta = TypeAdapter(list[Line])
        f.write(ta.dump_json(lines, indent=4).decode())


def combine_data():
    with open(GENERATED / "accesses.json", "r") as f:
        ta = TypeAdapter(list[Access])
        accesses = ta.validate_json(f.read())
    with open(GENERATED / "zones.json", "r") as f:
        ta = TypeAdapter(list[Zone])
        zones = ta.validate_json(f.read())
    with open(GENERATED / "lines.json", "r") as f:
        ta = TypeAdapter(list[Line])
        lines = ta.validate_json(f.read())
    with open(GENERATED / "zones_accesses_rel.json", "r") as f:
        ta = TypeAdapter(list[ZoneAccessRelationship])
        accesses_relationships = ta.validate_json(f.read())
    with open(GENERATED / "zones_lines_rel.json", "r") as f:
        ta = TypeAdapter(list[ZoneLineRelationship])
        lines_relationships = ta.validate_json(f.read())
    
    accesses_by_zone = defaultdict(list)
    for relationship in accesses_relationships:
        access = next(a for a in accesses if a.id == relationship.access_id)
        accesses_by_zone[relationship.zone_id].append(access)

    lines_by_zone = defaultdict(list)
    for relationship in lines_relationships:
        if relationship.mode != "METRO":
            continue
        line = next(l for l in lines if l.id == relationship.line_id)
        lines_by_zone[relationship.zone_id].append(line)

    zones_metro = [z for z in zones if z.type == "metroStation"]
    for zone_metro in zones_metro:
        zone_metro.accesses = accesses_by_zone[zone_metro.id]
        zone_metro.lines = lines_by_zone[zone_metro.id]

    with open(GENERATED / "zones_metro.json", "w") as f:
        ta = TypeAdapter(list[Zone])
        f.write(ta.dump_json(zones_metro, indent=4).decode())


if __name__ == "__main__":
    clean_transformations()
    transform_zones()
    tranform_access()
    transform_zone_access_relationships()
    transform_zone_line_relationships()
    extract_lines()
    combine_data()
