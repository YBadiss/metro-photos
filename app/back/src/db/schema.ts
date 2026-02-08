import {
  pgTable,
  text,
  integer,
  doublePrecision,
  primaryKey,
  serial,
  timestamp,
} from "drizzle-orm/pg-core";
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

export const photos = pgTable("photos", {
  id: serial("id").primaryKey(),
  s3Key: text("s3_key").notNull(),
  accessId: text("access_id").references(() => accesses.id),
  latitude: doublePrecision("latitude"),
  longitude: doublePrecision("longitude"),
  takenAt: timestamp("taken_at", { withTimezone: true }),
  camera: text("camera"),
  status: text("status").notNull().default("pending"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

// --- Relations ---

export const zonesRelations = relations(zones, ({ many }) => ({
  accesses: many(accesses),
  zoneLines: many(zoneLines),
}));

export const accessesRelations = relations(accesses, ({ one, many }) => ({
  zone: one(zones, { fields: [accesses.zoneId], references: [zones.id] }),
  photos: many(photos),
}));

export const photosRelations = relations(photos, ({ one }) => ({
  access: one(accesses, { fields: [photos.accessId], references: [accesses.id] }),
}));

export const linesRelations = relations(lines, ({ many }) => ({
  zoneLines: many(zoneLines),
}));

export const zoneLinesRelations = relations(zoneLines, ({ one }) => ({
  zone: one(zones, { fields: [zoneLines.zoneId], references: [zones.id] }),
  line: one(lines, { fields: [zoneLines.lineId], references: [lines.id] }),
}));
