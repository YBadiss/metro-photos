import { pgTable, text, integer, doublePrecision, primaryKey } from "drizzle-orm/pg-core";
import { relations } from "drizzle-orm";

// --- Tables ---

export const zones = pgTable("zones", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  type: text("type"),
  town: text("town").notNull(),
  postalRegion: text("postal_region").notNull(),
  xLambert93: integer("x_lambert_93").notNull(),
  yLambert93: integer("y_lambert_93").notNull(),
});

export const accesses = pgTable("accesses", {
  id: text("id").primaryKey(),
  zoneId: text("zone_id")
    .notNull()
    .references(() => zones.id),
  name: text("name").notNull(),
  shortName: integer("short_name"),
  xLambert93: integer("x_lambert_93").notNull(),
  yLambert93: integer("y_lambert_93").notNull(),
  lon: doublePrecision("lon").notNull(),
  lat: doublePrecision("lat").notNull(),
});

export const lines = pgTable("lines", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  color: text("color").notNull(),
  iconUrl: text("icon_url"),
  iconFilename: text("icon_filename"),
});

export const zoneLines = pgTable(
  "zone_lines",
  {
    zoneId: text("zone_id")
      .notNull()
      .references(() => zones.id),
    lineId: text("line_id")
      .notNull()
      .references(() => lines.id),
  },
  (t) => [primaryKey({ columns: [t.zoneId, t.lineId] })],
);

// --- Relations ---

export const zonesRelations = relations(zones, ({ many }) => ({
  accesses: many(accesses),
  zoneLines: many(zoneLines),
}));

export const accessesRelations = relations(accesses, ({ one }) => ({
  zone: one(zones, { fields: [accesses.zoneId], references: [zones.id] }),
}));

export const linesRelations = relations(lines, ({ many }) => ({
  zoneLines: many(zoneLines),
}));

export const zoneLinesRelations = relations(zoneLines, ({ one }) => ({
  zone: one(zones, { fields: [zoneLines.zoneId], references: [zones.id] }),
  line: one(lines, { fields: [zoneLines.lineId], references: [lines.id] }),
}));
