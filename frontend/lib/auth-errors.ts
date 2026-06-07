export function formatAuthRedirectError(message: string): string {
  const perEmailCooldown = message.match(/after (\d+) seconds/i);
  if (perEmailCooldown) {
    return `rate_limit:${perEmailCooldown[1]}`;
  }

  if (/email rate limit exceeded/i.test(message)) {
    return "email_rate_limit";
  }

  return message;
}

export function parseLoginError(error?: string) {
  if (!error) {
    return null;
  }

  if (error.startsWith("rate_limit:")) {
    const seconds = error.split(":")[1] ?? "1";
    return {
      type: "rate_limit" as const,
      seconds,
      message: `Please wait ${seconds} seconds before requesting another link. Check your inbox — the last email may already work.`,
    };
  }

  if (error === "email_rate_limit") {
    return {
      type: "email_rate_limit" as const,
      message:
        "Hourly email limit reached for this project (~2/hour on Supabase built-in mail). Wait a bit, use the last magic link in your inbox, or add RESEND_API_KEY to .env.local and run npm run configure:supabase.",
    };
  }

  return {
    type: "generic" as const,
    message: error,
  };
}
