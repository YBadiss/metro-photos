import "../env";
import { readFileSync } from "fs";
import { join } from "path";
import { db } from "./index";
import { zones, accesses, lines, zoneLines } from "./schema";

interface GeoPoint {
  lon: number;
  lat: number;
}
interface AccessData {
  id: string;
  name: string;
  short_name: number | null;
  x_lambert_93: number;
  y_lambert_93: number;
  geo_point: GeoPoint;
}
interface LineData {
  id: string;
  name: string;
  color: string;
  icon_url: string | null;
  icon_filename: string | null;
}
interface ZoneData {
  id: string;
  name: string;
  type: string | null;
  town: string;
  postal_region: string;
  x_lambert_93: number;
  y_lambert_93: number;
  accesses: AccessData[];
  lines: LineData[];
}

async function main() {
  const dataPath = join(process.cwd(), "data/zones_metro.json");
  const data: ZoneData[] = JSON.parse(readFileSync(dataPath, "utf-8"));

  console.log(`Seeding ${data.length} zones...`);

  // Collect unique lines across all zones
  const lineMap = new Map<string, LineData>();
  for (const zone of data) {
    for (const line of zone.lines) {
      lineMap.set(line.id, line);
    }
  }

  // Insert in order: zones, lines, accesses, zone_lines
  await db
    .insert(zones)
    .values(
      data.map((z) => ({
        id: z.id,
        name: z.name,
        type: z.type,
        town: z.town,
        postalRegion: z.postal_region,
        xLambert93: z.x_lambert_93,
        yLambert93: z.y_lambert_93,
      })),
    )
    .onConflictDoNothing();

  console.log(`Inserted ${data.length} zones`);

  const lineValues = Array.from(lineMap.values());
  await db
    .insert(lines)
    .values(
      lineValues.map((l) => ({
        id: l.id,
        name: l.name,
        color: l.color,
        iconUrl: l.icon_url,
        iconFilename: l.icon_filename,
      })),
    )
    .onConflictDoNothing();

  console.log(`Inserted ${lineValues.length} lines`);

  const accessValues = data.flatMap((z) =>
    z.accesses.map((a) => ({
      id: a.id,
      zoneId: z.id,
      name: a.name,
      shortName: a.short_name,
      xLambert93: a.x_lambert_93,
      yLambert93: a.y_lambert_93,
      lon: a.geo_point.lon,
      lat: a.geo_point.lat,
    })),
  );

  await db.insert(accesses).values(accessValues).onConflictDoNothing();

  console.log(`Inserted ${accessValues.length} accesses`);

  const zoneLinesValues = data.flatMap((z) =>
    z.lines.map((l) => ({
      zoneId: z.id,
      lineId: l.id,
    })),
  );

  await db.insert(zoneLines).values(zoneLinesValues).onConflictDoNothing();

  console.log(`Inserted ${zoneLinesValues.length} zone-line relationships`);

  console.log("Seed complete!");
  process.exit(0);
}

main();
