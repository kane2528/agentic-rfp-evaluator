"""Dynamic, evidence-grounded prompt builder."""
from __future__ import annotations

import json
from typing import Any


def build_evaluation_prompt(criteria: list[dict[str, Any]], supplier_name: str, document_text: str) -> str:
    criterion_spec = [{
        "criterion_id": int(c["criterion_id"]), "name": c["name"], "description": c["description"],
        "weight": float(c["weight"]), "max_score": float(c["max_score"]),
    } for c in criteria]
    return f"""You are the Evaluation Agent in a procurement evaluation workflow. Evaluate one supplier proposal.

Supplier metadata name: {supplier_name}
Active evaluation criteria loaded from SQLite:
{json.dumps(criterion_spec, ensure_ascii=False)}

Proposal text (the only source of evidence):
<proposal>
{document_text[:80000]}
</proposal>

Rules:
- Use ONLY evidence present in the supplier document.
- Do not invent certifications, prices, experience, features or claims.
- Return exactly one result for every active criterion listed above, using its criterion_id.
- Score only within the allowed range 0 through that criterion's max_score, inclusive.
- Include evidence supporting each score. If evidence is missing, explicitly say that evidence is not present rather than inventing it.
- Identify material proposal risks. Summarize the proposal accurately.
- Return JSON only, with no markdown or extra commentary, matching this schema:
{{"supplier_name":"{supplier_name}","criteria":[{{"criterion_id":1,"score":8,"max_score":10,"justification":"...","evidence":"..."}}],"risks":["..."],"overall_summary":"..."}}

Do not calculate final weighted scores, benchmarks, PPI, tie-breaks, or rankings."""
