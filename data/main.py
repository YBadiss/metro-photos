#!/usr/bin/env -S uv --quiet run --script
from collections import defaultdict
from pathlib import Path
from models import Zone, Access, ZoneAccessRelationship, ZoneLineRelationship, Line
from pydantic import TypeAdapter


def clean_transformations():
    for p in Path("generated_data_files/").glob("*.json"):
        p.unlink()


def transform_zones():
    ta = TypeAdapter(list[Zone])
    with open("source_data_files/zones-d-arrets.json", "r") as f:
        zones = ta.validate_json(f.read())
    with open("generated_data_files/zones.json", "w") as f:
        f.write(ta.dump_json(zones, indent=4).decode())


def tranform_access():
    ta = TypeAdapter(list[Access])
    with open("source_data_files/acces.json", "r") as f:
        accesses = ta.validate_json(f.read())
    with open("generated_data_files/accesses.json", "w") as f:
        f.write(ta.dump_json(accesses, indent=4).decode())


def transform_zone_access_relationships():
    ta = TypeAdapter(list[ZoneAccessRelationship])
    with open("source_data_files/relations-acces.json", "r") as f:
        accesses_relationships = ta.validate_json(f.read())
    with open("generated_data_files/zones_accesses_rel.json", "w") as f:
        f.write(ta.dump_json(accesses_relationships, indent=4).decode())


def transform_zone_line_relationships():
    ta = TypeAdapter(list[ZoneLineRelationship])
    with open("source_data_files/emplacement-des-gares-idf.json", "r") as f:
        line_relationships = ta.validate_json(f.read())
    with open("generated_data_files/zones_lines_rel.json", "w") as f:
        f.write(ta.dump_json(line_relationships, indent=4).decode())


def combine_data():
    with open("generated_data_files/accesses.json", "r") as f:
        ta = TypeAdapter(list[Access])
        accesses = ta.validate_json(f.read())
    with open("generated_data_files/zones.json", "r") as f:
        ta = TypeAdapter(list[Zone])
        zones = ta.validate_json(f.read())
    with open("generated_data_files/zones_accesses_rel.json", "r") as f:
        ta = TypeAdapter(list[ZoneAccessRelationship])
        accesses_relationships = ta.validate_json(f.read())
    with open("generated_data_files/zones_lines_rel.json", "r") as f:
        ta = TypeAdapter(list[ZoneLineRelationship])
        lines_relationships = ta.validate_json(f.read())
    
    accesses_by_zone = defaultdict(list)
    for relationship in accesses_relationships:
        access = next(a for a in accesses if a.id == relationship.access_id)
        accesses_by_zone[relationship.zone_id].append(access)

    lines = {}
    lines_by_zone = defaultdict(list)
    for relationship in lines_relationships:
        if relationship.mode != "METRO":
            continue
        if relationship.line_id not in lines:
            lines[relationship.line_id] = Line(
                id=relationship.line_id,
                name=relationship.line_name,
                icon_url=relationship.line_icon_url,
            )
        lines_by_zone[relationship.zone_id].append(lines[relationship.line_id])

    zones_metro = [z for z in zones if z.type == "metroStation"]
    for zone_metro in zones_metro:
        zone_metro.accesses = accesses_by_zone[zone_metro.id]
        zone_metro.lines = lines_by_zone[zone_metro.id]

    with open("generated_data_files/zones_metro.json", "w") as f:
        ta = TypeAdapter(list[Zone])
        f.write(ta.dump_json(zones_metro, indent=4).decode())


if __name__ == "__main__":
    clean_transformations()
    transform_zones()
    tranform_access()
    transform_zone_access_relationships()
    transform_zone_line_relationships()
    combine_data()
