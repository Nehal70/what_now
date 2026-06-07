def run(incident_type: str, state: str) -> str:
    state = (state or "unknown").strip()
    incident = (incident_type or "general").strip().lower()

    fault_rules = """FAULT RULES OVERVIEW:
- Pure comparative fault: You can recover even if mostly at fault (CA, NY, FL, etc.) — award reduced by your % fault
- Modified comparative (50% bar): No recovery if you are 50%+ at fault (CO, GA, etc.)
- Modified comparative (51% bar): No recovery if you are 51%+ at fault (TX, IL, etc.)
- Contributory negligence: Any fault bars recovery (AL, MD, NC, VA, DC) — very harsh

No-fault (PIP) states for auto: FL, MI, NJ, NY, PA, HI, KS, KY, MA, MN, ND, UT — limited lawsuit rights for minor injuries."""

    premises = """
PREMISES LIABILITY (slip and fall):
- Property owner owes duty of care to invitees (customers)
- Must prove: dangerous condition existed, owner knew or should have known, condition caused injury
- Notice: actual (they saw it) or constructive (should have discovered through reasonable inspection)
- Statute of limitations: typically 2-3 years from injury date (varies by state)"""

    lawyer_guidance = """
DO YOU NEED A LAWYER?
- Serious injury (surgery, permanent damage, lost wages): yes, consultation is worth it
- Minor bruise, fully recovered: often handle claim yourself
- Contributory negligence state + any possible fault on your part: strongly consider lawyer
- Most personal injury attorneys work on contingency (no upfront fee, ~33% of recovery)"""

    state_specific = ""
    state_lower = state.lower()
    state_map = {
        "california": "CA | Pure comparative fault | 2-year statute for personal injury | Strong tenant/invitee protections",
        "ca": "CA | Pure comparative fault | 2-year statute for personal injury | Strong tenant/invitee protections",
        "texas": "TX | Modified 51% comparative | 2-year statute | Business-friendly but recoverable with evidence",
        "tx": "TX | Modified 51% comparative | 2-year statute | Business-friendly but recoverable with evidence",
        "new york": "NY | Pure comparative | 3-year statute | No-fault for auto under $50k threshold",
        "ny": "NY | Pure comparative | 3-year statute | No-fault for auto under $50k threshold",
        "florida": "FL | Pure comparative | 2-year statute (recently reduced) | No-fault PIP for auto",
        "fl": "FL | Pure comparative | 2-year statute (recently reduced) | No-fault PIP for auto",
    }
    if state_lower in state_map:
        state_specific = f"\n\n{state.upper()} SPECIFICS:\n{state_map[state_lower]}"
    elif state_lower not in ("unknown", "", "n/a"):
        state_specific = f"\n\nFor {state}: Look up whether it is comparative or contributory negligence and the personal injury statute of limitations (usually 2-3 years)."

    next_step = """
CONCRETE NEXT STEP:
Document the scene now if still there. If injury is more than minor, schedule a medical evaluation today and keep all records."""

    return fault_rules + premises + lawyer_guidance + state_specific + next_step
