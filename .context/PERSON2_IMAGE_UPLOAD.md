# Person 2 — Backend Image Upload Implementation Guide

**Paste this into your agent/backend repo.** Person 1 has shipped the browser upload flow, Supabase storage, `/api/respond` shim, and LiveKit speak-on-send. Your backend must implement the contracts below.

---

## 0. What Person 1 already built (do not re-implement)

| Piece | Status |
|-------|--------|
| Browser GPS on `/` | ✅ `LocationCapture` → `POST /api/location` |
| Location on `__START__` only | ✅ Shim injects from stored user coords |
| `POST /api/sessions/{id}/images` | ✅ Upload to Supabase `session-images` bucket |
| `POST /api/sessions/{id}/images/send` | ✅ Calls your `/chat/stream` with `__IMAGE_UPLOAD__` |
| LiveKit speak on Send | ✅ Shim pushes `turn_complete` data packet → agent TTS |
| Upload UI | ✅ `/` + `/session/[id]` when `image_requested` fires |
| Dashboard thumbnails | ✅ `/dashboard` listens for `image_received` |
| `call_context` persisted per session | ✅ Updated after every turn in shim |

**Your job:** Qwen/tool logic, vision, `awaiting_image` signaling, `__IMAGE_UPLOAD__` handling, spoken responses.

---

## 1. System architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                         ACTIVE PHONE CALL                               │
├──────────────────────────────┬──────────────────────────────────────────┤
│  Phone (SIP audio)           │  Browser (logged in, same user)           │
│  User speaks                 │  User uploads JPEG/PNG/WebP               │
│       │                      │       │                                   │
│       ▼                      │       ▼                                   │
│  LiveKit Agent (Python)      │  POST /api/sessions/{id}/images           │
│       │                      │  (stage files in Supabase)              │
│       │ POST /api/respond    │       │                                   │
│       ▼                      │  User taps "Send N photos"                │
│  Person 1 shim ──────────────┼──────► POST .../images/send               │
│       │                      │       │                                   │
│       └──────────┬───────────┴───────┘                                   │
│                  ▼                                                         │
│         POST {BACKEND}/chat/stream  ◄── YOU IMPLEMENT THIS                │
│                  │                                                         │
│                  ├──► token / done SSE                                    │
│                  ├──► image_requested SSE (optional, recommended)         │
│                  └──► image_processed SSE (optional)                      │
│                  │                                                         │
│                  ▼                                                         │
│  Agent speaks response on phone (voice turn OR image-send turn)           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Conversation model (critical)

1. **Call keeps running** — user can keep talking on the phone while photos are pending.
2. **You ask for photos** — set `context.awaiting_image = true` and tell them to use the app.
3. **Wait state** — browser shows upload UI. Phone speech still works (normal turns, no `images[]`).
4. **User taps Send in browser** — Person 1 immediately calls your API with `__IMAGE_UPLOAD__` + `images[]`. **Not** waiting for the next phone utterance.
5. **You process vision** — merge into `context`, clear `awaiting_image`, return spoken `response`.
6. **Agent speaks immediately** — Person 1 pushes your `response` to the phone via LiveKit data message.

---

## 2. Endpoint you must implement: `POST /chat/stream`

Person 1 calls: `{BACKEND_ENDPOINT}/chat/stream`  
Headers: `Content-Type: application/json`, `ngrok-skip-browser-warning: true`  
Response: **SSE stream** (`data: {...}\n\n` lines)

### 2.1 Request body — all turns

```typescript
type ChatStreamRequest = {
  transcript: string;
  conversation_history: Array<{ role: "user" | "assistant"; text: string }>;
  context: CallContext;
  location?: { lat: number; lng: number };  // ONLY when transcript === "__START__"
  images?: SessionImage[];                   // ONLY when transcript === "__IMAGE_UPLOAD__"
};

type CallContext = {
  state?: string;
  incident_type?: string;
  signed_anything?: boolean;
  injury_severity?: string;
  witnesses?: boolean;
  tools_fired?: string[];
  disclaimer_given?: boolean;

  // ⭐ IMAGE FIELDS — YOU READ/WRITE THESE
  awaiting_image?: boolean;
  image_prompt?: string | null;
  scene_description?: string;  // suggested: set after vision
};

type SessionImage = {
  id: string;           // UUID from Person 1 DB
  url: string;          // HTTPS signed URL, 1-hour TTL — FETCH SERVER-SIDE
  mime_type: "image/jpeg" | "image/png" | "image/webp";
  uploaded_at: number;  // Unix ms
};
```

### 2.2 Sentinel transcripts

| `transcript` | Meaning | Person 1 sends |
|--------------|---------|----------------|
| `__START__` | First turn when call connects | Optional `location` |
| `__IMAGE_UPLOAD__` | User tapped Send in browser | `images[]` (1–3 items) |
| *(anything else)* | Normal phone STT text | No `images`, no `location` |

**Never** treat `__IMAGE_UPLOAD__` as spoken user text.

---

## 3. ⭐ HOW THE AGENT ASKS FOR IMAGES (implement this)

When your agent/tool decides a photo is needed:

### Step A — Verbal ask in `response`

The `done.response` string is spoken on the phone. Example:

> "If you can, open the What Now app on your phone browser and upload a picture of the floor where you slipped. Tap Send when you're ready."

### Step B — Set context flags in `done.context` (required)

```json
{
  "awaiting_image": true,
  "image_prompt": "Photo of the wet floor and any caution signs nearby"
}
```

Person 1's shim:
- Persists this to `sessions.call_context` in Supabase
- Emits `image_requested` SSE to browser/dashboard (also if you emit it — see Step C)

### Step C — Emit `image_requested` SSE (recommended)

On the same turn, before or after `done`, emit:

```json
{
  "type": "image_requested",
  "data": {
    "prompt": "Photo of the wet floor and any caution signs nearby"
  },
  "timestamp": 1717687381000
}
```

Person 1's shim forwards unknown SSE types `image_requested`, `image_processed`, `nearby_medical`, `nearby_legal` to the dashboard event bus.

### Step D — Keep `awaiting_image: true` until images arrive

While waiting:
- **Normal phone turns** — user may say "the manager is here" or "I can't take a photo right now". Handle normally. Keep `awaiting_image: true` unless they clearly won't send photos.
- **Do not** clear `awaiting_image` just because they spoke.

### Example `done` for asking turn

```json
{
  "type": "done",
  "response": "Open the What Now app and send me a photo of the scene when you can. I'll stay on the line.",
  "tool_called": "scene_guide",
  "reasoning": "Slip-and-fall at store — need visual confirmation of hazard before scene guidance",
  "latency_ms": 380,
  "phase": "gather",
  "context": {
    "state": "gather",
    "incident_type": "slip_and_fall",
    "awaiting_image": true,
    "image_prompt": "Photo of the wet area and surrounding aisle"
  }
}
```

---

## 4. ⭐ HANDLING `__IMAGE_UPLOAD__` (implement this)

Person 1 calls your stream when the user taps **Send all**:

```json
{
  "transcript": "__IMAGE_UPLOAD__",
  "conversation_history": [
    { "role": "user", "text": "I slipped on something near the produce section" },
    { "role": "assistant", "text": "Open the What Now app and send me a photo..." },
    { "role": "user", "text": "The manager is walking over" },
    { "role": "assistant", "text": "Stay calm. Don't sign anything yet." }
  ],
  "context": {
    "awaiting_image": true,
    "image_prompt": "Photo of the wet area and surrounding aisle",
    "incident_type": "slip_and_fall"
  },
  "images": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "url": "https://xxx.supabase.co/storage/v1/object/sign/session-images/userId/sessionId/abc.jpg?token=...",
      "mime_type": "image/jpeg",
      "uploaded_at": 1717687381000
    }
  ]
}
```

### Your processing steps

```
1. IF transcript != "__IMAGE_UPLOAD__" → skip this section
2. ASSERT images is non-empty array
3. FOR each image:
     a. HTTP GET image.url (server-side, follow redirects)
     b. Validate Content-Type matches mime_type
     c. Run vision model / multimodal Qwen
4. Merge vision output into context, e.g.:
     - scene_description: "Wet floor near produce, yellow caution sign tipped over"
     - hazards_visible: ["wet_floor", "blocked_sign"]
     - awaiting_image: false
     - image_prompt: null
5. Select appropriate tool if needed (scene_guide, moss_retrieval, etc.)
6. Craft voice-friendly response describing what you SEE and next steps
7. Return done event
8. OPTIONAL: emit image_processed SSE
```

### Example `done` after vision

```json
{
  "type": "done",
  "response": "I can see water on the floor near the produce section and a caution sign that's fallen over. Don't step in that area. If you can, take another photo from farther back, but only if it's safe.",
  "tool_called": "scene_guide",
  "reasoning": "Vision: wet floor + overturned sign confirms slip hazard. Providing scene guidance.",
  "latency_ms": 2400,
  "phase": "gather",
  "context": {
    "awaiting_image": false,
    "image_prompt": null,
    "incident_type": "slip_and_fall",
    "scene_description": "Water on produce aisle floor; yellow caution sign overturned",
    "hazards_visible": ["wet_floor", "overturned_sign"]
  }
}
```

Person 1 will:
- Persist messages + context
- Push `response` to LiveKit → **agent speaks on phone immediately**
- Update dashboard transcript

### Optional `image_processed` SSE

```json
{
  "type": "image_processed",
  "data": {
    "summary": "Wet floor near produce; overturned caution sign",
    "image_count": 1
  },
  "timestamp": 1717687381000
}
```

---

## 5. SSE stream format (full reference)

Each line: `data: {JSON}\n\n`

### Events you emit

| type | When | Payload |
|------|------|---------|
| `token` | Streaming text (optional) | `{ "content": "partial text" }` |
| `done` | **Required** every turn | See §5.1 |
| `image_requested` | You ask for photos | `{ "prompt": "string" }` |
| `image_processed` | After vision (optional) | `{ "summary": "string", "image_count": number }` |
| `nearby_medical` | Location features (separate) | `{ "places": [...] }` |
| `nearby_legal` | Location features (separate) | `{ "places": [...] }` |

**Do not** close the stream before all async events are sent if you emit delayed events (e.g. nearby places 10–30s later). Person 1 keeps reading until stream ends.

### 5.1 `done` event shape (required every turn)

```json
{
  "type": "done",
  "response": "string — WILL BE SPOKEN ON PHONE",
  "tool_called": "safety_check | scene_guide | moss_retrieval | insurance_tool | legal_tool | null",
  "reasoning": "string — shown on dashboard",
  "latency_ms": 1234,
  "phase": "triage | gather | inform | summarize",
  "context": { /* full updated context object */ }
}
```

**Rules:**
- `tool_called` must be exact enum string or `null`
- `context` must be the **complete** object (Person 1 replaces, not deep-merges)
- Always include `awaiting_image` explicitly (`true` or `false`)

---

## 6. Suggested agent / tool logic (pseudocode)

```python
async def handle_chat_stream(request: ChatStreamRequest) -> AsyncIterator[SSEEvent]:
    transcript = request.transcript
    ctx = request.context or {}
    history = request.conversation_history or []

    # ── First turn ──
    if transcript == "__START__":
        # location may be in request.location (one-time GPS from browser)
        lat, lng = (request.location or {}).get("lat"), (request.location or {}).get("lng")
        # Use for state law, nearby services, etc.
        ...

    # ── Image upload turn ──
    elif transcript == "__IMAGE_UPLOAD__":
        assert request.images, "Person 1 always sends images with __IMAGE_UPLOAD__"

        vision_results = []
        for img in request.images:
            bytes_ = await fetch_url(img.url)  # server-side HTTP GET
            analysis = await vision_model.analyze(bytes_, img.mime_type)
            vision_results.append(analysis)

        ctx["scene_description"] = synthesize_scene(vision_results)
        ctx["awaiting_image"] = False
        ctx["image_prompt"] = None

        response = craft_spoken_vision_summary(vision_results, ctx)
        tool = "scene_guide"  # or appropriate tool

        yield SSEEvent(type="image_processed", data={
            "summary": ctx["scene_description"],
            "image_count": len(request.images),
        })  # optional

        yield done(response=response, tool=tool, context=ctx, ...)

    # ── Normal voice turn ──
    else:
        user_text = transcript

        # If still waiting for photos, you MAY remind gently in response
        # but don't block other conversation
        needs_photo = should_request_scene_photo(user_text, ctx, history)

        if needs_photo and not ctx.get("awaiting_image"):
            ctx["awaiting_image"] = True
            ctx["image_prompt"] = "Photo of the incident scene"
            yield SSEEvent(type="image_requested", data={"prompt": ctx["image_prompt"]})
            response = "Please upload a photo in the What Now app. Tap Send when ready."
            ...
        else:
            response, tool, reasoning = await qwen_turn(user_text, history, ctx)
            ...

        yield done(response=response, tool=tool, context=ctx, ...)
```

### When to set `awaiting_image: true`

| Scenario | Ask? |
|----------|------|
| Slip/fall — need to see hazard | ✅ |
| Car accident — damage/scene | ✅ |
| Injury visible — user mentions wound | ✅ optional, sensitive |
| Insurance — card or document photo | ✅ |
| User says "I can't send photos" | ❌ clear `awaiting_image`, continue verbally |
| Legal phase only — no visual needed | ❌ |

---

## 7. Vision implementation notes

- **Fetch URLs server-side** within seconds of receive (1-hour signed URL TTL).
- **Do not** trust client-side descriptions of image content.
- **Handle failures gracefully:**
  - URL 403/404 → spoken: "I couldn't load the photo. Try sending again."
  - Keep `awaiting_image: true` on failure if still needed
- **Multiple images (up to 3):** analyze all; synthesize one combined `scene_description`.
- **Model:** Use Qwen-VL or your multimodal stack; Person 1 doesn't care which model as long as `response` is voice-friendly.

---

## 8. Voice response guidelines after vision

Responses are **spoken on a phone**. Write for audio:

- Short sentences (2–4 sentences typical)
- Describe what you see plainly: *"I see water on the floor and a fallen yellow sign."*
- Give one clear next action: *"Stay out of that area if you can."*
- Avoid markdown, bullet lists, JSON, URLs in `response`

---

## 9. Error handling matrix

| Situation | `awaiting_image` after | Example `response` |
|-----------|------------------------|-------------------|
| Images received + vision OK | `false` | "I can see…" |
| Images received + vision failed | `true` | "I had trouble analyzing the photo. Can you send another with better lighting?" |
| User speaks, no upload yet | `true` (usually) | Answer their question + optional gentle reminder |
| User says can't upload | `false` | "That's okay. Describe what you see…" |
| `__IMAGE_UPLOAD__` but empty images[] | `true` | Should not happen; return error response |

---

## 10. curl test script

```bash
BACKEND="https://your-ngrok.ngrok-free.dev"

# 1) Normal turn — should NOT ask for image yet (depends on your logic)
curl -N -X POST "$BACKEND/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "I just fell at the grocery store",
    "conversation_history": [],
    "context": {}
  }'

# 2) Simulate asking for photo (your backend should emit awaiting_image)
#    Inspect SSE for done.context.awaiting_image === true

# 3) Simulate browser Send
curl -N -X POST "$BACKEND/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "__IMAGE_UPLOAD__",
    "conversation_history": [
      {"role":"user","text":"I just fell at the grocery store"},
      {"role":"assistant","text":"Please upload a photo in the app."}
    ],
    "context": {
      "awaiting_image": true,
      "image_prompt": "Photo of the floor"
    },
    "images": [{
      "id": "test-1",
      "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Fronalpstock_rocks.jpg/320px-Fronalpstock_rocks.jpg",
      "mime_type": "image/jpeg",
      "uploaded_at": 1717687381000
    }]
  }'

# Expect: awaiting_image false, spoken summary in done.response
```

---

## 11. Integration checklist (copy into your PR)

### Signaling (agent asks)
- [ ] Tool/logic decides when photo is needed
- [ ] `done.context.awaiting_image = true` on ask turn
- [ ] `done.context.image_prompt` set with user-facing instruction
- [ ] `done.response` verbally tells user to open app and upload
- [ ] `image_requested` SSE emitted (recommended)

### Receiving (browser sends)
- [ ] Branch on `transcript === "__IMAGE_UPLOAD__"`
- [ ] Server-side fetch of each `images[].url`
- [ ] Vision analysis for 1–3 images
- [ ] Update `context` with findings (`scene_description`, etc.)
- [ ] `done.context.awaiting_image = false` on success
- [ ] Voice-friendly `done.response` describing what was seen
- [ ] Optional `image_processed` SSE

### Normal turns while waiting
- [ ] Phone speech works without `images[]`
- [ ] `awaiting_image` stays true until upload or user opts out
- [ ] Context returned in full on every `done`

### Location (already live from Person 1)
- [ ] On `__START__`, read optional `location: { lat, lng }` once
- [ ] Persist in your session state for the call

---

## 12. Limits enforced by Person 1

| Limit | Value |
|-------|-------|
| Images per Send | 3 max |
| File size | 5 MB each |
| MIME types | `image/jpeg`, `image/png`, `image/webp` |
| Signed URL TTL | 3600 seconds |

---

## 13. Contact / contract changes

If you need a different sentinel than `__IMAGE_UPLOAD__`, or a separate `/vision` endpoint, coordinate **before** demo day. The following are **locked**:

- Browser Send → immediate `/chat/stream` call (not next phone turn)
- `awaiting_image` + `image_prompt` in `context`
- Agent speaks `done.response` immediately after image send (via Person 1 LiveKit push)
- Images as signed HTTPS URLs, not base64 in JSON

---

## 14. File reference on Person 1 side (for debugging)

| File | Role |
|------|------|
| `app/api/sessions/[id]/images/route.ts` | Upload staging |
| `app/api/sessions/[id]/images/send/route.ts` | Triggers `__IMAGE_UPLOAD__` |
| `lib/backend-chat.ts` | Forwards to your `/chat/stream`, parses SSE |
| `lib/respond-turn.ts` | Persists context, emits events, notifies agent |
| `lib/livekit-notify.ts` | Pushes `turn_complete` to phone agent |
| `components/ImageUploadPanel.tsx` | Browser UI |
| `agent/agent.py` | `handle_turn_complete` speaks image response |

---

*End of Person 2 implementation guide.*
