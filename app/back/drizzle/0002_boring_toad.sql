ALTER TABLE "photos" ALTER COLUMN "access_id" DROP NOT NULL;--> statement-breakpoint
ALTER TABLE "photos" ADD COLUMN "status" text DEFAULT 'pending' NOT NULL;