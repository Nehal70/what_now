OWN_POLICY_TRIGGERS = [
    "my insurance",
    "my own insurance",
    "my policy",
    "will insurance cover",
    "who pays my",
    "medical bills",
    "who covers",
    "my medpay",
    "my coverage",
    "do i have coverage",
    "my progressive",
    "my state farm",
    "my allstate",
    "my geico",
    "my deductible",
    "my collision",
    "will my insurance",
    "worried about bills",
    "afford the bills",
    "pay for this",
    "cover the bills",
]


def build_policy_moss_query(incident_type: str, state: str) -> str:
    incident = (incident_type or "car accident").replace("_", " ")
    state = (state or "Texas").strip()
    return (
        f"Progressive policy MedPay collision coverage {state} "
        f"{incident} medical bills what covered TX-2847-JAK-2024"
    )


def run(incident_type: str, state: str) -> str:
    state = (state or "unknown").strip()
    incident = (incident_type or "general").strip().lower()

    general = """INSURANCE CLAIM GUIDANCE

How to file:
1. Report the incident to the property owner's insurer or your own insurer within 24-72 hours
2. Get the claim number in writing
3. Keep all receipts: medical, transportation, missed work
4. Do not give a recorded statement until you understand your rights

What adjusters look for:
- Inconsistencies between your statement and medical records
- Pre-existing conditions they can blame
- Gaps in medical treatment (they argue injury wasn't serious)
- Social media posts showing activity inconsistent with injury

What NOT to say on recorded statement:
- "I'm fine" or "It wasn't that bad"
- "It was partly my fault"
- "I didn't see the hazard" (implies you weren't paying attention)
- Speculation about what caused the fall

Common denial tactics:
- "No defect existed" — counter with photos and witness statements
- "You were trespassing" — counter with your status as customer/invitee
- "Injury is pre-existing" — your doctor can distinguish new vs old injury

Time limits:
- Most states: 2-3 years to file lawsuit, but report to insurer within days/weeks
- PIP (no-fault) states: often 14-30 days to file PIP claim

Reservation of rights: Insurer may pay while reserving right to deny later — do not assume acceptance means full coverage."""

    if incident in ("slip and fall", "slip/fall", "premises"):
        specific = """
SLIP AND FALL SPECIFICS:
- Report to store's general liability carrier (ask manager for insurance info)
- Business may have self-insured retention — still file formally
- Denial tactic: "Floor was dry" — your photos and witness statements are critical
- Denial tactic: "Open and obvious hazard" — you may still recover in comparative fault states"""
    elif incident in ("car accident", "auto", "motor vehicle", "hit_run", "hit and run"):
        specific = """
AUTO ACCIDENT SPECIFICS:
- File with your insurer AND at-fault driver's insurer
- MedPay on your own policy covers your medical bills regardless of fault
- Uninsured motorist coverage if other driver has no insurance
- Do not accept first settlement offer — it is usually low"""
    else:
        specific = f"\nFor {incident_type}: follow general steps above and document everything."

    state_note = ""
    if state.lower() not in ("unknown", "", "n/a"):
        state_note = f"\n\nState note ({state}): Check your state's statute of limitations (typically 2-3 years for personal injury). Report to insurer promptly — delays can give them grounds to deny."

    policy_note = (
        "\n\nOWN POLICY: User has Progressive TX-2847-JAK-2024. "
        "MedPay $10,000, collision $500 deductible, claims 1-800-776-4737. "
        "Use Moss policy details for specific coverage language."
    )

    return general + specific + state_note + policy_note
