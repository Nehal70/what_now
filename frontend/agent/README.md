# Phone calling setup

Voice runs on your **physical phone** via LiveKit SIP. Person 2's backend (ngrok) stays the brain.

## 1. Add secrets to `.env.local`

Open `frontend/.env.local` and add:

```bash
# Supabase service role — Project Settings → API → service_role (secret)
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# Shared secret between the Python agent and Next.js internal routes
INTERNAL_API_SECRET=pick_a_long_random_string

# LiveKit phone number (after you buy one in LiveKit Cloud)
LIVEKIT_PHONE_NUMBER=+1XXXXXXXXXX
NEXT_PUBLIC_PHONE_NUMBER=+1XXXXXXXXXX

# Agent dispatch name — must match LiveKit dispatch rule
AGENT_NAME=what-now-agent

# Where the agent calls back (use ngrok if agent runs on another machine)
NEXTJS_URL=http://localhost:3000
```

**Where to find the Supabase service role key:**
1. Go to [supabase.com/dashboard](https://supabase.com/dashboard)
2. Open project `jmyqbaeintkjpavtdmur`
3. **Project Settings** → **API**
4. Copy **service_role** under Project API keys (keep it secret)

## 2. LiveKit phone number + dispatch rule

In [LiveKit Cloud](https://cloud.livekit.io):

1. **Telephony** → **Phone Numbers** → buy a US number
2. Create a **dispatch rule**:
   - Type: **Individual** (one room per caller)
   - Room prefix: `call-`
   - Agent dispatch: `what-now-agent` (same as `AGENT_NAME`)
   - Do **not** hide caller phone number
3. Assign the rule to your number
4. Put the number in `.env.local` as above

## 3. Run the app

Terminal 1 — Next.js:

```bash
cd frontend
npm run dev
```

Terminal 2 — LiveKit agent:

```bash
cd frontend/agent
pip install -r requirements.txt
python agent.py dev
```

## 4. Register your phone

1. Open http://localhost:3000 and log in
2. Go to **Phone** in the nav (or `/settings/phone`)
3. Save the **same cell number** you will call from

## 5. Test

1. Keep http://localhost:3000 open on your dashboard
2. Dial your LiveKit number from that phone
3. A **Live call** card should appear
4. Click it to see the transcript update as you talk

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Session not created | Check `SUPABASE_SERVICE_ROLE_KEY` and `INTERNAL_API_SECRET` |
| "Phone not registered" | Save your number at `/settings/phone` — must match caller ID |
| Agent doesn't answer | Agent worker running? Dispatch rule `agentName` = `what-now-agent`? |
| No AI responses | Person 2 ngrok URL in `BACKEND_ENDPOINT` must be up |
