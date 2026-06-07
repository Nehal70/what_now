/** Normalize user input to E.164 (US-focused; accepts +1XXXXXXXXXX or 10-digit US). */
export function normalizePhoneE164(input: string): string | null {
  const digits = input.replace(/\D/g, "");
  if (digits.length === 10) {
    return `+1${digits}`;
  }
  if (digits.length === 11 && digits.startsWith("1")) {
    return `+${digits}`;
  }
  if (input.trim().startsWith("+") && digits.length >= 10 && digits.length <= 15) {
    return `+${digits}`;
  }
  return null;
}

export function formatPhoneDisplay(e164: string): string {
  const digits = e164.replace(/\D/g, "");
  if (digits.length === 11 && digits.startsWith("1")) {
    const area = digits.slice(1, 4);
    const mid = digits.slice(4, 7);
    const last = digits.slice(7);
    return `(${area}) ${mid}-${last}`;
  }
  return e164;
}
