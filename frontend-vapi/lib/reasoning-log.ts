export type ReasoningLevel =
  | "BOOT"
  | "ASK"
  | "ROUTE"
  | "TOOL"
  | "DEMO"
  | "PHASE"
  | "INFO";

export type ReasoningLogEntry = {
  id: string;
  time: string;
  level: ReasoningLevel;
  message: string;
  detail?: string;
  tools?: string[];
};

const DEMO_TURN_LABELS: Record<number, { message: string; tools?: string[] }> = {
  1: { message: "Rear-end collision — safety & scene check" },
  2: { message: "Police report required — do not leave without one" },
  3: { message: "Warn caller not to sign anything at scene" },
  4: {
    message: "State Farm adjuster script — refuse recorded statement",
    tools: ["insurance_tool", "moss_retrieval", "legal_tool"],
  },
  5: {
    message: "Progressive MedPay — file medical claim today",
    tools: ["insurance_tool", "moss_retrieval"],
  },
  6: {
    message: "Settlement floor + push urgent care tonight",
    tools: ["legal_tool", "moss_retrieval"],
  },
};

const LEVEL_COLORS: Record<ReasoningLevel, string> = {
  BOOT: "#9ed4f5",
  ASK: "#ff6b4a",
  ROUTE: "#9b6bff",
  TOOL: "#5fd4a0",
  DEMO: "#ff6b4a",
  PHASE: "#9ed4f5",
  INFO: "rgba(255,255,255,0.55)",
};

export function levelColor(level: ReasoningLevel): string {
  return LEVEL_COLORS[level];
}

function formatTime(date = new Date()): string {
  return date.toLocaleTimeString("en-US", { hour12: false });
}

function extractQuoted(text: string): string | undefined {
  const match = text.match(/'([^']+)'/);
  return match?.[1];
}

function parseToolsFromText(text: string): string[] | undefined {
  const arrow = text.match(/→\s*(.+)$/);
  if (!arrow) return undefined;
  return arrow[1]
    .split(/[,→]/)
    .map((t) => t.trim())
    .filter(Boolean);
}

export function parseReasoning(raw: string, at = new Date()): ReasoningLogEntry {
  const trimmed = raw.trim();
  const id = `${at.getTime()}-${trimmed.slice(0, 32)}`;

  if (!trimmed || trimmed === "Initial greeting") {
    return {
      id,
      time: formatTime(at),
      level: "BOOT",
      message: "Agent online — starting triage",
    };
  }

  const questioning = trimmed.match(/^Questioning:\s*filling gap/i);
  if (questioning) {
    const gap = extractQuoted(trimmed);
    return {
      id,
      time: formatTime(at),
      level: "ASK",
      message: "Gathering missing incident detail",
      detail: gap ? `Next question: "${gap}"` : undefined,
    };
  }

  const demoTagged = trimmed.match(/^Demo T(\d+)\s*[—-]\s*(.+)$/i);
  if (demoTagged) {
    const turn = Number(demoTagged[1]);
    const spec = DEMO_TURN_LABELS[turn];
    return {
      id,
      time: formatTime(at),
      level: "DEMO",
      message: demoTagged[2].trim(),
      detail: spec ? `Caller turn ${turn}` : undefined,
      tools: spec?.tools,
    };
  }

  const demoTurn = trimmed.match(/^Final demo script turn\s+(\d+)/i);
  if (demoTurn) {
    const turn = Number(demoTurn[1]);
    const spec = DEMO_TURN_LABELS[turn];
    return {
      id,
      time: formatTime(at),
      level: "DEMO",
      message: spec?.message ?? `Demo script — turn ${turn}`,
      detail: `Caller turn ${turn}`,
      tools: spec?.tools,
    };
  }

  const intentOverride = trimmed.match(/^Intent override:\s*(.+)$/i);
  if (intentOverride) {
    const tools = parseToolsFromText(intentOverride[1]);
    return {
      id,
      time: formatTime(at),
      level: "ROUTE",
      message: "Intent rerouted to better tool match",
      detail: intentOverride[1],
      tools,
    };
  }

  const classifiedConversational = trimmed.match(
    /^Phase\s+(\w+):\s*classified\s+(\w+),\s*conversational/i,
  );
  if (classifiedConversational) {
    const [, phase, intent] = classifiedConversational;
    return {
      id,
      time: formatTime(at),
      level: "ROUTE",
      message: `Classified "${intent}" — responding without tools`,
      detail: `${phase} phase`,
    };
  }

  const classified = trimmed.match(
    /^Phase\s+(\w+):\s*classified\s+(\w+)\s*→\s*(.+)/i,
  );
  if (classified) {
    const [, phase, intent, toolTail] = classified;
    const tools = toolTail.split(",").map((t) => t.trim()).filter(Boolean);
    return {
      id,
      time: formatTime(at),
      level: "ROUTE",
      message: `Classified "${intent}" in ${phase} phase`,
      tools,
    };
  }

  const phaseTools = trimmed.match(/^Phase\s+(\w+):\s*(.+)$/i);
  if (phaseTools) {
    const [, phase, tail] = phaseTools;
    if (/conversational/i.test(tail)) {
      return {
        id,
        time: formatTime(at),
        level: "PHASE",
        message: `${phase} phase — direct response`,
      };
    }
    const tools = tail.split(",").map((t) => t.trim()).filter(Boolean);
    return {
      id,
      time: formatTime(at),
      level: "PHASE",
      message: `${phase} phase — running tools`,
      tools,
    };
  }

  const selected = trimmed.match(/^Selected\s+(.+?)\s+based on user situation/i);
  if (selected) {
    const tools = selected[1].split(",").map((t) => t.trim());
    return {
      id,
      time: formatTime(at),
      level: "TOOL",
      message: "Tool chain selected for caller context",
      tools,
    };
  }

  return {
    id,
    time: formatTime(at),
    level: "INFO",
    message: trimmed,
  };
}

/** Skip exact duplicate back-to-back reasoning (common with streaming + webhook). */
export function shouldSkipReasoning(
  previous: ReasoningLogEntry[],
  raw: string,
): boolean {
  if (previous.length === 0) return false;
  const last = previous[previous.length - 1];
  const next = parseReasoning(raw);
  const lastKey = `${last.level}|${last.message}|${last.detail ?? ""}|${(last.tools ?? []).join(",")}`;
  const nextKey = `${next.level}|${next.message}|${next.detail ?? ""}|${(next.tools ?? []).join(",")}`;
  return lastKey === nextKey;
}

export function appendReasoning(
  previous: ReasoningLogEntry[],
  raw: string,
  max = 30,
): ReasoningLogEntry[] {
  if (!raw.trim() || shouldSkipReasoning(previous, raw)) {
    return previous;
  }
  return [...previous, parseReasoning(raw)].slice(-max);
}
