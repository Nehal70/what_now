/**
 * Configures Supabase Auth for local demo/dev.
 *
 * Always applies URL + relaxed OTP rate limits.
 * If RESEND_API_KEY is in .env.local, also wires custom SMTP so you can
 * send to multiple emails (built-in Supabase mail is capped at ~2/hour).
 *
 * Requires SUPABASE_ACCESS_TOKEN in .env.local.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const PROJECT_REF = "jmyqbaeintkjpavtdmur";
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

function loadEnvFile() {
  try {
    return readFileSync(resolve(process.cwd(), ".env.local"), "utf8");
  } catch {
    return "";
  }
}

function loadFromEnv(env, key) {
  if (process.env[key]) {
    return process.env[key];
  }

  const match = env.match(new RegExp(`^${key}=(.+)$`, "m"));
  return match?.[1]?.trim() ?? null;
}

const envFile = loadEnvFile();
const token = loadFromEnv(envFile, "SUPABASE_ACCESS_TOKEN");

if (!token) {
  console.error(
    "Missing SUPABASE_ACCESS_TOKEN. Add it to .env.local:\n" +
      "  SUPABASE_ACCESS_TOKEN=sbp_...\n" +
      "Create one at https://supabase.com/dashboard/account/tokens",
  );
  process.exit(1);
}

/** Dev-friendly limits (no custom SMTP required). */
const body = {
  site_url: SITE_URL,
  uri_allow_list: `${SITE_URL}/**`,
  // Same email: wait only 1s between magic-link requests
  smtp_max_frequency: 1,
  // Project-wide OTP/magic-link budget per hour
  rate_limit_otp: 100,
  rate_limit_verify: 100,
};

const resendKey = loadFromEnv(envFile, "RESEND_API_KEY");
const smtpFrom =
  loadFromEnv(envFile, "SMTP_FROM_EMAIL") ?? "onboarding@resend.dev";

if (resendKey) {
  Object.assign(body, {
    external_email_enabled: true,
    smtp_admin_email: smtpFrom,
    smtp_host: "smtp.resend.com",
    smtp_port: 465,
    smtp_user: "resend",
    smtp_pass: resendKey,
    smtp_sender_name: "What Now",
    // With custom SMTP you can raise the hourly email cap (built-in is ~2/hour)
    rate_limit_email_sent: 100,
  });
  console.log("RESEND_API_KEY found — configuring custom SMTP");
} else {
  console.log(
    "No RESEND_API_KEY — OTP limits relaxed, but built-in email stays ~2/hour.\n" +
      "Add RESEND_API_KEY to .env.local and re-run for multi-email demo testing.",
  );
}

const response = await fetch(
  `https://api.supabase.com/v1/projects/${PROJECT_REF}/config/auth`,
  {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  },
);

if (!response.ok) {
  const text = await response.text();
  console.error(`Failed (${response.status}): ${text}`);
  process.exit(1);
}

const config = await response.json();
console.log("\nSupabase auth configured for demo/dev:");
console.log(`  site_url:              ${config.site_url}`);
console.log(`  uri_allow_list:        ${config.uri_allow_list}`);
console.log(`  smtp_max_frequency:    ${config.smtp_max_frequency}s between sends (same email)`);
console.log(`  rate_limit_otp:        ${config.rate_limit_otp}/hour (project-wide)`);
console.log(`  rate_limit_verify:     ${config.rate_limit_verify}/hour`);
console.log(
  `  rate_limit_email_sent: ${config.rate_limit_email_sent ?? "(built-in ~2/hour)"}/hour`,
);
if (config.smtp_host) {
  console.log(`  smtp_host:             ${config.smtp_host}`);
  console.log(`  smtp_admin_email:      ${config.smtp_admin_email}`);
}
