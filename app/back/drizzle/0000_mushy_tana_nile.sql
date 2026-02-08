CREATE TABLE "accesses" (
	"id" text PRIMARY KEY NOT NULL,
	"zone_id" text NOT NULL,
	"name" text NOT NULL,
	"short_name" integer,
	"x_lambert_93" integer NOT NULL,
	"y_lambert_93" integer NOT NULL,
	"lon" double precision NOT NULL,
	"lat" double precision NOT NULL
);
--> statement-breakpoint
CREATE TABLE "lines" (
	"id" text PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"color" text NOT NULL,
	"icon_url" text,
	"icon_filename" text
);
--> statement-breakpoint
CREATE TABLE "zone_lines" (
	"zone_id" text NOT NULL,
	"line_id" text NOT NULL,
	CONSTRAINT "zone_lines_zone_id_line_id_pk" PRIMARY KEY("zone_id","line_id")
);
--> statement-breakpoint
CREATE TABLE "zones" (
	"id" text PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"type" text,
	"town" text NOT NULL,
	"postal_region" text NOT NULL,
	"x_lambert_93" integer NOT NULL,
	"y_lambert_93" integer NOT NULL
);
--> statement-breakpoint
ALTER TABLE "accesses" ADD CONSTRAINT "accesses_zone_id_zones_id_fk" FOREIGN KEY ("zone_id") REFERENCES "public"."zones"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "zone_lines" ADD CONSTRAINT "zone_lines_zone_id_zones_id_fk" FOREIGN KEY ("zone_id") REFERENCES "public"."zones"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "zone_lines" ADD CONSTRAINT "zone_lines_line_id_lines_id_fk" FOREIGN KEY ("line_id") REFERENCES "public"."lines"("id") ON DELETE no action ON UPDATE no action;