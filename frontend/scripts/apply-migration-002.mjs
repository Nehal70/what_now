import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const PROJECT_REF = "jmyqbaeintkjpavtdmur";

function loadToken() {
  const env = readFileSync(resolve(process.cwd(), ".env.local"), "utf8");
  return env.match(/^SUPABASE_ACCESS_TOKEN=(.+)$/m)?.[1]?.trim() ?? null;
}

async function query(token, sql) {
  const res = await fetch(
    `https://api.supabase.com/v1/projects/${PROJECT_REF}/database/query`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query: sql }),
    },
  );
  const text = await res.text();
  if (!res.ok) {
    throw new Error(`${res.status} ${text}`);
  }
  return text ? JSON.parse(text) : null;
}

const token = loadToken();
if (!token) {
  console.error("Missing SUPABASE_ACCESS_TOKEN in .env.local");
  process.exit(1);
}

const migrationPath = resolve(
  process.cwd(),
  "supabase/migrations/002_session_images.sql",
);
const sql = readFileSync(migrationPath, "utf8");

console.log("Applying 002_session_images.sql ...");
await query(token, sql);
console.log("Migration applied successfully.");
