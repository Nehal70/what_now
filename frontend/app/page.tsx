import { redirect } from "next/navigation";

import HomeDashboard from "@/app/home-dashboard";
import HomeMarketing from "@/app/home-marketing";
import { getPlanFromMetadata } from "@/lib/plan";
import { createClient } from "@/lib/supabase/server";

export default async function Home() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return <HomeMarketing />;
  }

  if (!getPlanFromMetadata(user.user_metadata)) {
    redirect("/choose-plan");
  }

  return <HomeDashboard email={user.email ?? "Signed in"} userId={user.id} />;
}
