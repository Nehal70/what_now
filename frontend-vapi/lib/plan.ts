export const FREE_PLAN = "free" as const;

export type UserPlan = typeof FREE_PLAN;

export function getPlanFromMetadata(
  metadata: Record<string, unknown> | undefined,
): UserPlan | null {
  return metadata?.plan === FREE_PLAN ? FREE_PLAN : null;
}

export function getPostAuthPath(
  metadata: Record<string, unknown> | undefined,
): "/" | "/choose-plan" {
  return getPlanFromMetadata(metadata) ? "/" : "/choose-plan";
}
