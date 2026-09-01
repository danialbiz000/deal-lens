"""run_ic_simulation(bundle, bear_case_gate_input, client) -> 5-role
transcript + recommendation (design doc section 4).

5 SEQUENTIAL Claude calls -- Analyst -> Industry -> Credit -> Risk -> IC
Chair -- each seeing the bundle plus every prior role's structured output.
This is why it is 5 calls and not a single multi-turn generation: it
matches the spec's own agent-workflow diagram exactly, a real sequential
debate rather than five independent takes.

The critical piece: `finance_engine.ic_gate.evaluate_bear_case_thresholds`
runs in CODE after the IC Chair call, independent of what the LLM said. If
the gate fails AND the LLM said PROCEED_TO_DD, the final recommendation is
forced to HOLD -- both `llm_recommendation` (raw) and `recommendation`
(final, possibly overridden) are persisted by the caller, so an override is
always visible and auditable, never silent.
"""

import json
from typing import Any, Dict, List

from app.ai.citation_validation import validate_citations
from app.ai.client import ClaudeClient
from app.ai.prompts import ic_analyst, ic_chair, ic_credit, ic_industry, ic_risk
from finance_engine.ic_gate import BearCaseInput, evaluate_bear_case_thresholds

ROLE_ORDER = ["analyst", "industry", "credit", "risk", "ic_chair"]
_ROLE_MODULES = {
    "analyst": ic_analyst,
    "industry": ic_industry,
    "credit": ic_credit,
    "risk": ic_risk,
    "ic_chair": ic_chair,
}


def _build_user_prompt(bundle: Dict[str, Any], prior_outputs: List[Dict[str, Any]]) -> str:
    parts = [f"Source bundle -- the only facts you may cite:\n{json.dumps(bundle, indent=2)}"]
    if prior_outputs:
        parts.append("Prior role outputs, in sequential order:\n" + json.dumps(prior_outputs, indent=2))
    else:
        parts.append("You are the first role to see this case -- there is no prior output yet.")
    return "\n\n".join(parts)


def _validate_role_output(output: Dict[str, Any], bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Run citation validation over every prose field in a role's output
    (every field here is either a string or a list of strings), same as
    memo sections.
    """
    reports = []
    for value in output.values():
        texts = value if isinstance(value, list) else [value]
        for text in texts:
            if isinstance(text, str):
                reports.append(validate_citations(text, bundle))

    return {
        "total_citations": sum(r.total_citations for r in reports),
        "invalid_citations": [c for r in reports for c in r.invalid_citations],
        "mismatched_citations": [c for r in reports for c in r.mismatched_citations],
        "uncited_numbers": [n for r in reports for n in r.uncited_numbers],
        "status": "warnings" if any(r.status == "warnings" for r in reports) else "ok",
    }


def run_ic_simulation(
    bundle: Dict[str, Any], bear_case_gate_input: BearCaseInput, client: ClaudeClient
) -> Dict[str, Any]:
    transcript: List[Dict[str, Any]] = []
    prior_outputs: List[Dict[str, Any]] = []

    for role in ROLE_ORDER:
        module = _ROLE_MODULES[role]
        output = client.complete_structured(
            system=module.SYSTEM_PROMPT,
            user=_build_user_prompt(bundle, prior_outputs),
            json_schema=module.JSON_SCHEMA,
        )
        validation_report = _validate_role_output(output, bundle)

        transcript.append({"role": role, "output": output, "validation_report": validation_report})
        prior_outputs.append({"role": role, **output})

    ic_chair_output = transcript[-1]["output"]
    llm_recommendation = ic_chair_output["llm_recommendation"]

    gate = evaluate_bear_case_thresholds(bear_case_gate_input)
    if not gate.passes and llm_recommendation == "PROCEED_TO_DD":
        final_recommendation = "HOLD"
        override_fired = True
        override_reason = "; ".join(gate.failures)
    else:
        final_recommendation = llm_recommendation
        override_fired = False
        override_reason = None

    return {
        "transcript": transcript,
        "llm_recommendation": llm_recommendation,
        "recommendation": final_recommendation,
        "override_fired": override_fired,
        "override_reason": override_reason,
        "key_strengths": ic_chair_output["key_strengths"],
        "key_risks": ic_chair_output["key_risks"],
        "unanswered_dd": ic_chair_output["unanswered_dd"],
        "gate_failures": gate.failures,
    }
