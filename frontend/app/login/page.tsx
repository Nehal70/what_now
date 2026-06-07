import Link from "next/link";

import { parseLoginError } from "@/lib/auth-errors";

import { sendMagicLink } from "./actions";

type LoginPageProps = {
  searchParams: Promise<{
    sent?: string;
    error?: string;
  }>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const { sent, error } = await searchParams;
  const loginError = parseLoginError(error);

  return (
    <main className="mx-auto flex min-h-full max-w-md flex-col justify-center px-6 py-16">
      <Link
        href="/"
        className="mb-8 text-sm text-white/60 transition hover:text-white"
      >
        ← Back
      </Link>

      <h1 className="font-[family-name:var(--font-baskerville)] text-3xl italic">
        Sign in or sign up
      </h1>
      <p className="mt-2 text-sm text-white/70">
        One form for both — enter your email and we&apos;ll send a magic link.
        No password needed.
      </p>

      {sent ? (
        <p className="mt-6 rounded-lg border border-[#9ed4f5]/30 bg-[#9ed4f5]/10 px-4 py-3 text-sm text-[#9ed4f5]">
          Check your email for the sign-in link.
        </p>
      ) : null}

      {loginError ? (
        <p
          className={`mt-6 rounded-lg border px-4 py-3 text-sm ${
            loginError.type === "rate_limit" ||
            loginError.type === "email_rate_limit"
              ? "border-[#9ed4f5]/30 bg-[#9ed4f5]/10 text-[#9ed4f5]"
              : "border-[#ff6b4a]/30 bg-[#ff6b4a]/10 text-[#ff6b4a]"
          }`}
        >
          {loginError.message}
        </p>
      ) : null}

      <form action={sendMagicLink} className="mt-8 flex flex-col gap-4">
        <label className="flex flex-col gap-2 text-sm">
          Email
          <input
            id="email"
            name="email"
            type="email"
            required
            autoComplete="email"
            placeholder="you@example.com"
            className="rounded-lg border border-white/15 bg-white/5 px-4 py-3 outline-none ring-[#9ed4f5] focus:ring-2"
          />
        </label>
        <button
          type="submit"
          className="rounded-lg bg-[#ff6b4a] px-4 py-3 font-medium text-black transition hover:bg-[#ff8266]"
        >
          Send magic link
        </button>
      </form>
    </main>
  );
}
