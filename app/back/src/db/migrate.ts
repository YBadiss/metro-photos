import "../env";
import { drizzle } from "drizzle-orm/postgres-js";
import { migrate } from "drizzle-orm/postgres-js/migrator";
import postgres from "postgres";

async function main() {
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    throw new Error("DATABASE_URL environment variable is required");
  }

  // Use max 1 connection for migrations
  const client = postgres(databaseUrl, { max: 1 });
  const db = drizzle(client);

  await migrate(db, { migrationsFolder: "./drizzle" });

  console.log("Migrations complete!");
  await client.end();
}

main();
