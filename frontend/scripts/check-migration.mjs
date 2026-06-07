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
  return JSON.parse(text);
}

const token = loadToken();
if (!token) {
  console.error("Missing SUPABASE_ACCESS_TOKEN in .env.local");
  process.exit(1);
}

const checks = await query(
  token,
  `select
    exists (
      select 1 from information_schema.columns
      where table_schema = 'public' and table_name = 'sessions' and column_name = 'call_context'
    ) as has_call_context,
    exists (
      select 1 from information_schema.tables
      where table_schema = 'public' and table_name = 'session_images'
    ) as has_session_images,
    exists (
      select 1 from storage.buckets where id = 'session-images'
    ) as has_storage_bucket`,
);

console.log(JSON.stringify(checks, null, 2));
