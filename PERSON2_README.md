# What Now? — Person 2: Intelligence, Tools & Knowledge Base

## What you own
- Qwen as the reasoning brain (tool-calling LLM)
- All 5 tools Qwen can call
- Unsiloed knowledge base (the entire legal/insurance corpus)
- Moss semantic retrieval sitting over the KB
- TrueFoundry as the gateway wrapping all Qwen calls
- The FastAPI backend Person 1's frontend calls

## What you are NOT building
- LiveKit / voice / phone (Person 1)
- Frontend UI / dashboard (Person 1)
- SSE event stream (Person 1)

---

## Your single job in one sentence
Build a POST endpoint at `/chat` that receives a transcript + conversation history, runs it through Qwen (via TrueFoundry) with 5 tools available, returns a plain JSON response with the answer, which tool fired, reasoning trace, and latency.

---

## The contract with Person 1 — agree on this first

**They send you:**
```json
{
  "transcript": "I slipped on a wet floor at a grocery store",
  "conversation_history": [
    { "role": "user", "text": "I slipped on a wet floor" },
    { "role": "assistant", "text": "Are you safe? Can you move?" }
  ]
}
```

**You send back:**
```json
{
  "response": "Do not sign anything the manager hands you.",
  "tool_called": "scene_guide",
  "reasoning": "User at scene, manager approaching — scene guidance needed before legal",
  "latency_ms": 312
}
```

`tool_called` must be exactly one of:
- `safety_check`
- `scene_guide`
- `moss_retrieval`
- `insurance_tool`
- `legal_tool`

---

## Stack

| Layer | Tech |
|---|---|
| Backend | Python + FastAPI |
| LLM | Qwen (via TrueFoundry gateway) |
| Tool calling | Qwen function calling / tool use API |
| Knowledge base | Unsiloed (document ingestion + retrieval API) |
| Semantic search | Moss (retrieval over Unsiloed KB) |
| Gateway | TrueFoundry (wraps all Qwen calls) |
| Hosting | Local for hackathon, expose via ngrok |

---

## Repo structure — tell Cursor to scaffold this

```
what-now-backend/
├── main.py                   # FastAPI app + /chat endpoint
├── agent.py                  # Qwen tool-calling loop
├── tools/
│   ├── __init__.py
│   ├── safety_check.py       # Triage logic
│   ├── scene_guide.py        # Scene documentation guidance
│   ├── moss_retrieval.py     # Moss search over Unsiloed KB
│   ├── insurance_tool.py     # Insurance claims lookup
│   └── legal_tool.py         # State law + legal rights lookup
├── knowledge_base/
│   ├── ingest.py             # Unsiloed ingestion script
│   ├── retrieval.py          # Moss retrieval wrapper
│   └── docs/                 # Raw KB documents (txt/pdf)
│       ├── insurance_claims.txt
│       ├── state_fault_laws.txt
│       ├── premises_liability.txt
│       ├── personal_injury.txt
│       └── what_not_to_say.txt
├── prompts/
│   └── system_prompt.txt     # Qwen system prompt
├── .env                      # All secrets
└── requirements.txt
```

---

## Environment variables

```bash
# TrueFoundry
TRUEFOUNDRY_ENDPOINT=https://your-truefoundry-endpoint/v1/chat/completions
TRUEFOUNDRY_API_KEY=

# Qwen model name (through TrueFoundry)
QWEN_MODEL=qwen-plus   # or qwen-turbo, qwen-max

# Unsiloed
UNSILOED_API_KEY=
UNSILOED_KB_ID=        # created after ingestion

# Moss
MOSS_API_KEY=
MOSS_INDEX_ID=         # created after indexing

# Server
PORT=8000
```

---

## Step 0 — Setup

```bash
mkdir what-now-backend && cd what-now-backend
python -m venv venv && source venv/bin/activate
pip install fastapi uvicorn openai httpx python-dotenv
```

Expose locally to Person 1 via ngrok:
```bash
ngrok http 8000
# give Person 1 the https URL as BACKEND_ENDPOINT
```

---

## CURSOR PROMPT 1 — FastAPI skeleton + /chat endpoint

Paste this into Cursor:

```
Create a FastAPI app in main.py with a single POST endpoint at /chat.

Request body (Pydantic model):
- transcript: str
- conversation_history: list of dicts with role (str) and text (str)

Response body:
- response: str
- tool_called: str or None
- reasoning: str or None
- latency_ms: int

The endpoint should:
1. Record start time
2. Call agent.py run_agent(transcript, conversation_history)
3. Record end time, compute latency_ms
4. Return the result

Also add a GET /health endpoint that returns {"status": "ok"}.

Add CORS middleware allowing all origins (we are demoing locally).

Load env vars from .env using python-dotenv.
```

---

## CURSOR PROMPT 2 — Qwen tool-calling agent

Paste this into Cursor:

```
Create agent.py with a function run_agent(transcript, conversation_history) that:

1. Builds a messages array for the Qwen API:
   - System message: read from prompts/system_prompt.txt
   - Convert conversation_history (role/text dicts) to OpenAI format (role/content)
   - Append the new transcript as the latest user message

2. Defines 5 tools for Qwen function calling:
   - safety_check: takes no args, returns safety triage guidance
   - scene_guide: takes no args, returns scene documentation steps
   - moss_retrieval: takes query (str), calls Moss to search the KB
   - insurance_tool: takes incident_type (str) and state (str), returns claims procedure
   - legal_tool: takes incident_type (str) and state (str), returns legal rights

3. Calls the Qwen API through TrueFoundry endpoint (OpenAI-compatible):
   - Use TRUEFOUNDRY_ENDPOINT and TRUEFOUNDRY_API_KEY from env
   - Use QWEN_MODEL from env
   - Pass the tools as functions
   - Set max_tokens=500, temperature=0.3

4. Checks the response:
   - If Qwen returns a tool_call: execute the matching tool from tools/ directory, then make a second Qwen call with the tool result appended, get the final response
   - If no tool_call: use the direct response

5. Returns a dict: { response, tool_called, reasoning }

Use the openai Python client pointed at TRUEFOUNDRY_ENDPOINT.
```

---

## CURSOR PROMPT 3 — System prompt

Paste this into Cursor:

```
Create prompts/system_prompt.txt with this content:

You are What Now, a calm and knowledgeable voice assistant for people who have just been injured.

Your role is incident guidance — you help people protect themselves legally and financially in the critical minutes after an injury. You are NOT a lawyer. You NEVER say "you have a case" or "you will win". You say "you may have rights" or "it's worth speaking to a lawyer."

You are:
- Calm. The user is scared. Speak slowly and clearly.
- Empathetic. Always acknowledge their situation before giving guidance.
- Actionable. Give concrete next steps, not vague advice.
- Brief. Short sentences. One thing at a time.

You have 5 tools available. Use them based on what the user needs right now:
- safety_check: use first, always. Make sure they are safe before anything else.
- scene_guide: use when they are still at the scene and need to document or interact with others.
- moss_retrieval: use when you need specific legal or insurance information to answer accurately.
- insurance_tool: use when they ask about filing a claim or dealing with their insurer.
- legal_tool: use when they ask about their rights, fault, or whether they need a lawyer.

When you use moss_retrieval, incorporate the result naturally into your response. Do not say "according to my retrieval" — just speak it as knowledge.

The user called you immediately after getting hurt. They are shaking. Make them feel less alone first, then guide them.

Start every first response with: "I'm here. First — are you safe?"
```

---

## CURSOR PROMPT 4 — Knowledge base documents

Paste this into Cursor:

```
Create the following files in knowledge_base/docs/ with realistic, detailed content:

1. state_fault_laws.txt
Include: at-fault vs no-fault states list, comparative vs contributory negligence rules, pure comparative fault states, modified comparative fault states (50% and 51% bars). Cover all 50 states. Format as: STATE | FAULT TYPE | RULE | KEY NOTE

2. premises_liability.txt
Include: definition of premises liability, duty of care (invitee vs licensee vs trespasser), what constitutes a dangerous condition, notice requirement (actual vs constructive notice), slip and fall specifically, what to document at scene, statute of limitations by state for premises liability, what voids a claim.

3. insurance_claims.txt
Include: how to file a claim step by step, what adjusters look for, common denial reasons and how to counter them, what NOT to say to an adjuster, recorded statement rights, time limits for filing, PIP vs liability coverage, uninsured motorist coverage, what "reservation of rights" means.

4. personal_injury.txt
Include: what qualifies as personal injury, types (slip/fall, dog bite, car accident, workplace, assault), damages (economic vs non-economic), how cases are valued, statute of limitations by incident type, when you need a lawyer vs when you don't, contingency fee explained simply.

5. what_not_to_say.txt
Include: exact phrases that void claims ("I'm fine", "It was my fault", "I didn't see the sign"), why each phrase is dangerous legally, what to say instead, how insurance adjusters use recorded statements, why apologizing is dangerous, what to say to police vs what to say to the other party.
```

---

## CURSOR PROMPT 5 — Unsiloed ingestion

Paste this into Cursor:

```
Create knowledge_base/ingest.py that:

1. Reads all .txt files from knowledge_base/docs/
2. For each file, calls the Unsiloed API to ingest the document into a knowledge base
3. Uses UNSILOED_API_KEY from env
4. Prints the KB ID after creation — save this as UNSILOED_KB_ID in .env
5. Handles errors gracefully and prints progress

Use httpx for HTTP calls. Unsiloed API base: https://api.unsiloed.ai
Check Unsiloed docs for exact ingestion endpoint — it is typically POST /v1/documents with the text content and a metadata object.

After writing this, I will run: python knowledge_base/ingest.py
```

---

## CURSOR PROMPT 6 — Moss retrieval wrapper

Paste this into Cursor:

```
Create knowledge_base/retrieval.py with a function search_kb(query: str) -> str that:

1. Takes a search query string
2. Calls the Moss API to perform semantic search over the Unsiloed KB
3. Uses MOSS_API_KEY and MOSS_INDEX_ID from env
4. Returns the top 3 results concatenated as a single string
5. Includes a fallback: if Moss returns no results, return "No specific information found for this query."
6. Times the request and prints latency to console

Moss API base: check Moss documentation — semantic search endpoint is typically POST /v1/search with { query, index_id, top_k }.

This function will be called by tools/moss_retrieval.py.
```

---

## CURSOR PROMPT 7 — The 5 tools

Paste this into Cursor:

```
Create the following tool files in tools/. Each tool is a Python function that returns a string. The string is what Qwen receives as the tool result and incorporates into its answer.

tools/safety_check.py
Function: run() -> str
Returns a structured triage checklist:
- Check if they can move safely
- Signs of serious injury (head, spine, can't bear weight)
- When to call 911 immediately vs when it's safe to stay
- Reassurance phrase to use

tools/scene_guide.py  
Function: run() -> str
Returns step-by-step scene documentation:
- Exactly what to photograph (floor condition, signage, injury, wider area)
- What NOT to say to the other party or store manager
- How to fill out an incident report safely (what to write, what to leave blank)
- How to collect witness information
- Whether to call police and what to say

tools/moss_retrieval.py
Function: run(query: str) -> str
Imports search_kb from knowledge_base/retrieval.py
Calls search_kb(query) and returns the result
Adds a header: f"[Knowledge base result for: {query}]\n{result}"

tools/insurance_tool.py
Function: run(incident_type: str, state: str) -> str
Returns insurance guidance specific to incident_type and state:
- How to file the claim
- What the adjuster will ask
- What NOT to say on the recorded statement
- Common denial tactics for this incident type
- Time limit to file in this state
If state is unknown, return general guidance.

tools/legal_tool.py
Function: run(incident_type: str, state: str) -> str
Returns legal rights information:
- Fault rules for this state
- Whether they likely need a lawyer
- Statute of limitations for this incident type in this state
- What "premises liability" or relevant legal theory applies
- One concrete next step
Always end with: "This is general information, not legal advice. If your injury is serious, speaking with a personal injury attorney (most offer free consultations) is worth doing."
```

---

## CURSOR PROMPT 8 — Wire everything up and test

Paste this into Cursor:

```
Now wire everything together and add a test script.

In agent.py, make sure:
- The 5 tool functions are imported from tools/
- When Qwen calls a tool, the correct function is called with the correct arguments
- The tool result is appended to messages and Qwen is called again for final response
- The tool_called name is captured and returned

Create test_agent.py that runs 4 test scenarios without needing the full server:

Scenario 1: "I just slipped on a wet floor at a grocery store, my wrist hurts"
Expected tool: safety_check

Scenario 2: "I'm okay, the manager just came over and wants me to fill out a form"  
Expected tool: scene_guide

Scenario 3: "Should I get a lawyer? This is in California"
Expected tool: legal_tool

Scenario 4: "How do I file an insurance claim for this?"
Expected tool: insurance_tool

Print the response and tool_called for each. Run with: python test_agent.py
```

---

## CURSOR PROMPT 9 — Final integration check

Paste this into Cursor:

```
Start the FastAPI server: uvicorn main:app --reload --port 8000

Then create test_endpoint.py that sends POST requests to http://localhost:8000/chat with each of the 4 test scenarios and prints the full JSON response including response, tool_called, reasoning, latency_ms.

Also add a __START__ handler in main.py: if transcript == "__START__", skip the agent and return:
{
  "response": "I'm here. First — are you safe? Are you hurt?",
  "tool_called": "safety_check",
  "reasoning": "Initial greeting",
  "latency_ms": 0
}

This is what Person 1's frontend sends on first load.
```

---

## Build order — your 5 hours

| Hour | Cursor Prompt | Done when |
|---|---|---|
| Hour 1 | Prompt 1 + 2 + 3 | FastAPI running, Qwen callable via TrueFoundry, system prompt set |
| Hour 2 | Prompt 4 + 5 | KB documents written, Unsiloed ingestion working, KB ID saved |
| Hour 3 | Prompt 6 + 7 | Moss retrieval live, all 5 tools returning real data |
| Hour 4 | Prompt 8 | Full tool-calling loop tested against all 4 scenarios |
| Hour 5 | Prompt 9 + integration with Person 1 | Endpoint tested end to end with real voice input |

---

## TrueFoundry setup (do manually before Hour 1)

1. Sign in to TrueFoundry dashboard
2. Create a new AI Gateway
3. Add Qwen as a model provider (use Alibaba Cloud / DashScope API key)
4. Get your gateway endpoint URL + API key
5. Set both in .env as TRUEFOUNDRY_ENDPOINT and TRUEFOUNDRY_API_KEY
6. Test with a raw curl:
```bash
curl -X POST $TRUEFOUNDRY_ENDPOINT \
  -H "Authorization: Bearer $TRUEFOUNDRY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen-plus", "messages": [{"role": "user", "content": "hello"}]}'
```

---

## Common issues

**Qwen not calling tools:** Make sure tools are passed in OpenAI `tools` format (not `functions`). Qwen via TrueFoundry uses the OpenAI-compatible API. Tool format: `[{ "type": "function", "function": { "name": ..., "description": ..., "parameters": ... } }]`

**Unsiloed ingestion fails:** Check their docs for exact content-type and body format. Some versions want multipart/form-data, others want JSON with base64.

**Moss returns empty:** Make sure MOSS_INDEX_ID matches the index you built over Unsiloed. They need to be linked.

**TrueFoundry 401 errors:** Double check the Authorization header format — some gateways want `Bearer token`, others want `token` directly.

**Response too long / slow:** Set max_tokens=300 for voice — long responses sound bad when spoken. Keep Qwen on-point with the system prompt.

---

## Sponsor callouts for submission writeup

- **Qwen:** Core reasoning brain — all tool-calling decisions, response synthesis, and conversation management run through Qwen via the TrueFoundry gateway
- **Unsiloed:** Powers the entire knowledge base — 5 documents covering 50-state law, insurance procedures, premises liability, personal injury, and scene guidance are ingested and served via Unsiloed
- **Moss:** Real-time semantic retrieval over the Unsiloed KB — the moss_retrieval tool performs sub-500ms vector search to pull the exact legal or insurance fact Qwen needs mid-conversation
- **TrueFoundry:** Every single Qwen call is routed through TrueFoundry gateway — full observability, governance, and rate management across all tool-calling loops
