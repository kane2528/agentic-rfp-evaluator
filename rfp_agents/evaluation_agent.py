"""Evaluation Agent: calls a JSON-capable OpenAI-compatible LLM or deterministic demo."""
from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

from prompts.evaluation_prompt import build_evaluation_prompt


DEMO_SCORES = {
    "apex systems": {"technical capability": 9.3, "implementation plan": 7.6, "commercial value": 6.1, "security & compliance": 9.5, "support & experience": 7.1},
    "brightpath tech": {"technical capability": 7.2, "implementation plan": 9.1, "commercial value": 9.6, "security & compliance": 4.4, "support & experience": 5.2},
    "nexaworks": {"technical capability": 8.6, "implementation plan": 9.6, "commercial value": 8.1, "security & compliance": 8.3, "support & experience": 9.6},
    "orbit digital": {"technical capability": 7.1, "implementation plan": 6.7, "commercial value": 7.9, "security & compliance": 7.4, "support & experience": 9.2},
}


class EvaluationAgentError(RuntimeError):
    pass


def demo_evaluation(supplier_name: str, criteria: list[dict[str, Any]], document_text: str) -> dict[str, Any]:
    key = supplier_name.strip().casefold()
    profile = DEMO_SCORES.get(key)
    if profile is None:
        # A transparent fallback for user-supplied documents; criteria-specific keyword
        # signals make demo mode repeatable while keeping the run inside the normal pipeline.
        text = document_text.casefold()
        values = []
        for c in criteria:
            name = c["name"].casefold()
            keywords = {
                "technical": ("architecture", "integration", "scalable", "api"),
                "implementation": ("milestone", "timeline", "delivery", "team"),
                "commercial": ("price", "cost", "fixed fee", "assumption"),
                "security": ("security", "encryption", "privacy", "audit"),
                "support": ("support", "reference", "experience", "service"),
            }
            group = next((k for k in keywords if k in name), "")
            count = sum(word in text for word in keywords.get(group, ()))
            values.append(min(float(c["max_score"]), 4.0 + count * 1.2))
        profile = {str(c["name"]).casefold(): values[i] for i, c in enumerate(criteria)}
    criteria_results = []
    for i, c in enumerate(criteria):
        score = profile.get(str(c["name"]).casefold(), float(c["max_score"]) * 0.65)
        score = min(float(c["max_score"]), score)
        criteria_results.append({"criterion_id": int(c["criterion_id"]), "score": score,
                                 "max_score": float(c["max_score"]),
                                 "justification": f"Demo score based on the supplied synthetic proposal profile for {c['name']}.",
                                 "evidence": _demo_evidence(c["name"], supplier_name, document_text)})
    risks_by_supplier = {
        "apex systems": ["Premium pricing may exceed the available budget."],
        "brightpath tech": ["Compliance details and delivery experience are limited."],
        "nexaworks": ["Commercial assumptions should be confirmed during negotiation."],
        "orbit digital": ["The integration approach is described at a high level."],
    }
    return {"supplier_name": supplier_name, "criteria": criteria_results,
            "risks": risks_by_supplier.get(key, ["Demo mode uses heuristic scores; confirm findings with a configured LLM."]),
            "overall_summary": f"Deterministic DEMO evaluation of {supplier_name}. Review the cited proposal evidence and criterion details."}


def _demo_evidence(criterion: str, supplier_name: str, text: str) -> str:
    terms = criterion.lower().replace("&", " ").split()
    lines = [line.strip() for line in text.splitlines() if any(term in line.casefold() for term in terms)]
    if lines:
        return "Proposal text: " + " ".join(lines[:2])[:380]
    return f"Synthetic proposal for {supplier_name}; see the {criterion} section."


def evaluate(supplier_name: str, criteria: list[dict[str, Any]], document_text: str) -> tuple[dict[str, Any], str]:
    api_key = os.getenv("LLM_API_KEY", "").strip()
    if not api_key:
        return demo_evaluation(supplier_name, criteria, document_text), "DEMO"
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    try:
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "90"))
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=1)
        prompt = build_evaluation_prompt(criteria, supplier_name, document_text)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": "Return only a JSON object that follows the requested evaluation schema."},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
        )
        content = response.choices[0].message.content
        if not content:
            raise EvaluationAgentError("LLM returned an empty response.")
        return content, "LLM"
    except EvaluationAgentError:
        raise
    except Exception as exc:
        raise EvaluationAgentError(f"LLM evaluation failed: {exc}") from exc
