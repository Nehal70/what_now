import Link from "next/link";
import { redirect } from "next/navigation";

import { getPlanFromMetadata } from "@/lib/plan";
import { createClient } from "@/lib/supabase/server";

import { selectFreePlan } from "./actions";

type ChoosePlanPageProps = {
  searchParams: Promise<{
    error?: string;
  }>;
};

export default async function ChoosePlanPage({ searchParams }: ChoosePlanPageProps) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  if (getPlanFromMetadata(user.user_metadata)) {
    redirect("/");
  }

  const { error } = await searchParams;

  return (
    <main className="mx-auto flex min-h-full max-w-lg flex-col justify-center px-6 py-16">
      <h1 className="font-[family-name:var(--font-baskerville)] text-3xl italic">
        Choose a plan
      </h1>
      <p className="mt-2 text-sm text-white/70">
        Pick how you want to use What Now. You can change this later.
      </p>

      {error ? (
        <p className="mt-6 rounded-lg border border-[#ff6b4a]/30 bg-[#ff6b4a]/10 px-4 py-3 text-sm text-[#ff6b4a]">
          {error}
        </p>
      ) : null}

      <form action={selectFreePlan} className="mt-8">
        <button
          type="submit"
          className="w-full rounded-xl border border-white/10 bg-white/5 p-6 text-left transition hover:border-[#9ed4f5]/40 hover:bg-white/[0.07]"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-white/40">
                Free
              </p>
              <p className="mt-2 font-[family-name:var(--font-baskerville)] text-2xl italic">
                $0<span className="text-base not-italic text-white/50">/month</span>
              </p>
              <p className="mt-3 text-sm text-white/65">
                Get started with the demo dashboard and phone guidance flow.
              </p>
            </div>
            <span className="shrink-0 rounded-full bg-[#ff6b4a] px-4 py-2 text-sm font-medium text-black">
              Select
            </span>
          </div>
        </button>
      </form>

      <p className="mt-6 text-center text-xs text-white/35">
        Signed in as {user.email}
      </p>

      <Link
        href="/"
        className="mt-8 text-center text-sm text-white/50 transition hover:text-white"
      >
        ← Back to home
      </Link>
    </main>
  );
}
