export type ConversationMessage = {
  role: "user" | "assistant";
  text: string;
};

export type SessionStatus = "active" | "completed";

export type Session = {
  id: string;
  userId: string;
  status: SessionStatus;
  callerPhone: string;
  livekitRoom: string | null;
  phase: string | null;
  title: string | null;
  startedAt: string;
  endedAt: string | null;
};

export type SessionMessage = {
  id: string;
  sessionId: string;
  role: "user" | "assistant";
  text: string;
  createdAt: string;
};

/** Mirrors backend IncidentStack.data persisted in sessions.call_context */
export type IncidentStackData = {
  incident_type?: string | null;
  location?: string | null;
  state?: string | null;
  store_name?: string | null;
  injuries?: string | null;
  can_move?: boolean | null;
  still_at_scene?: boolean | null;
  witnesses?: boolean | null;
  signed_anything?: boolean | null;
  questions_asked?: string[];
  phase?: string;
  turns?: number;
  has_guided?: boolean;
  tools_fired?: string[];
  other_carrier?: string | null;
  nearby_legal_fired?: boolean;
  disclaimer_given?: boolean;
};

export type CallContext = {
  state?: string;
  incident_type?: string;
  signed_anything?: boolean;
  injury_severity?: string;
  witnesses?: boolean;
  tools_fired?: string[];
  disclaimer_given?: boolean;
  awaiting_image?: boolean;
  image_prompt?: string | null;
  scene_description?: string;
  incident_stack?: IncidentStackData;
  other_carrier?: string | null;
  nearby_legal_fired?: boolean;
  stack_phase?: string;
  has_guided?: boolean;
  questions_asked?: string[];
  turns?: number;
  injuries?: string | null;
  still_at_scene?: boolean | null;
};

export type SessionImagePayload = {
  id: string;
  url: string;
  mime_type: string;
  uploaded_at: number;
};

export type SessionImageRecord = {
  id: string;
  sessionId: string;
  userId: string;
  storagePath: string;
  mimeType: string;
  status: "staged" | "sent";
  createdAt: string;
  sentAt: string | null;
};

export type UserLocation = {
  lat: number;
  lng: number;
};

export type OrbState = "idle" | "listening" | "thinking" | "speaking";

export type ToolName =
  | "safety_check"
  | "scene_guide"
  | "moss_retrieval"
  | "insurance_tool"
  | "legal_tool"
  | null;

export const IMAGE_UPLOAD_TOKEN = "__IMAGE_UPLOAD__";
export const START_TOKEN = "__START__";
export const SILENCE_TOKEN = "__USER_SILENT__";

export type SSEEvent = {
  type:
    | "transcript"
    | "tool"
    | "reasoning"
    | "latency"
    | "call_state"
    | "phase"
    | "image_requested"
    | "image_received"
    | "image_processed";
  data: unknown;
  timestamp: number;
};
