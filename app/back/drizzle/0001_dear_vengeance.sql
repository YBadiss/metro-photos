CREATE TABLE "photos" (
	"id" serial PRIMARY KEY NOT NULL,
	"s3_key" text NOT NULL,
	"access_id" text NOT NULL,
	"latitude" double precision,
	"longitude" double precision,
	"taken_at" timestamp with time zone,
	"camera" text,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "photos" ADD CONSTRAINT "photos_access_id_accesses_id_fk" FOREIGN KEY ("access_id") REFERENCES "public"."accesses"("id") ON DELETE no action ON UPDATE no action;