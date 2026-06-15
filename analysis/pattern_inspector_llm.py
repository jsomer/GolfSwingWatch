"""Optional LLM narrative for Pattern Inspector reports."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
REQUEST_TIMEOUT_SECONDS = 45


class LLMConfigurationError(RuntimeError):
    """Raised when LLM narration is requested but not configured."""


class LLMRequestError(RuntimeError):
    """Raised when the LLM provider returns an error."""


def llm_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def _compact_patterns(patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for pattern in patterns:
        item = {
            "kind": pattern.get("kind"),
            "title": pattern.get("title"),
            "summary": pattern.get("summary"),
        }
        if pattern.get("kind") == "fault":
            item["low_prevalence"] = pattern.get("low_prevalence")
            item["high_prevalence"] = pattern.get("high_prevalence")
        if pattern.get("kind") == "metric":
            item["low_average"] = pattern.get("low_average")
            item["high_average"] = pattern.get("high_average")
            item["delta_ratio"] = pattern.get("delta_ratio")
        compact.append(item)
    return compact


def build_llm_context(report: dict[str, Any]) -> dict[str, Any]:
    """Build a compact, auditable payload for the LLM (no raw sensor data)."""
    return {
        "swing_count": report.get("swing_count"),
        "low_rated_count": report.get("low_rated_count"),
        "high_rated_count": report.get("high_rated_count"),
        "low_rating_threshold": report.get("low_rating_threshold"),
        "high_rating_threshold": report.get("high_rating_threshold"),
        "practice": report.get("practice"),
        "phase_chain": report.get("phase_chain"),
        "low_rated_faults": report.get("low_rated_faults"),
        "high_rated_faults": report.get("high_rated_faults"),
        "low_rated_metrics": report.get("low_rated_metrics"),
        "high_rated_metrics": report.get("high_rated_metrics"),
        "patterns": _compact_patterns(report.get("patterns", [])),
        "notes": (
            "Most swings are practice swings without reliable ball contact. "
            "Tempo is backswing_duration / downswing_duration from wrist motion phases."
        ),
    }


def _system_prompt() -> str:
    return (
        "You are a golf practice-swing analyst reviewing computed cohort statistics from "
        "an Apple Watch motion pipeline. You only receive aggregated metrics and fault flags — "
        "never raw sensor streams.\n\n"
        "Rules:\n"
        "- Ground every claim in the provided JSON. Do not invent numbers or swing counts.\n"
        "- Assume practice swings unless the data says otherwise; do not treat missing contact as a flaw.\n"
        "- Compare low-rated vs high-rated cohorts when both exist.\n"
        "- Prefer fault flags and metric deltas already listed under patterns.\n"
        "- Write 2 short paragraphs plus up to 3 bullet recommendations.\n"
        "- Use plain language suitable for an amateur golfer.\n"
        "- If patterns is empty, say more varied rated swings are needed and mention what to watch for."
    )


def _chat_completions_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def generate_llm_narrative(
    report: dict[str, Any],
    *,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> str:
    """Call an OpenAI-compatible chat API and return narrative text."""
    resolved_key = (
        api_key.strip()
        if api_key is not None
        else os.getenv("OPENAI_API_KEY", "").strip()
    )
    if not resolved_key:
        raise LLMConfigurationError(
            "OPENAI_API_KEY is not set. Export your key or pass api_key explicitly."
        )

    resolved_model = (model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL).strip()
    resolved_base = (base_url or os.getenv("OPENAI_BASE_URL") or DEFAULT_BASE_URL).strip()
    context = build_llm_context(report)

    payload = {
        "model": resolved_model,
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": _system_prompt()},
            {
                "role": "user",
                "content": (
                    "Summarize the swing cohort patterns in this JSON. "
                    "Cite specific metrics and fault rates from the data.\n\n"
                    f"{json.dumps(context, indent=2)}"
                ),
            },
        ],
    }

    request = urllib.request.Request(
        _chat_completions_url(resolved_base),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {resolved_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise LLMRequestError(f"LLM request failed ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise LLMRequestError(f"LLM request failed: {exc.reason}") from exc

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMRequestError(f"Unexpected LLM response shape: {body}") from exc

    narrative = str(content).strip()
    if not narrative:
        raise LLMRequestError("LLM returned an empty narrative.")
    return narrative


def attach_llm_narrative(
    report: dict[str, Any],
    *,
    enabled: bool = True,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    """Add llm_narrative / llm_error / llm_model fields to a pattern report."""
    report = dict(report)
    if not enabled:
        report["llm_narrative"] = None
        report["llm_error"] = None
        report["llm_model"] = None
        return report

    try:
        resolved_model = (model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL).strip()
        report["llm_narrative"] = generate_llm_narrative(
            report,
            api_key=api_key,
            model=model,
            base_url=base_url,
        )
        report["llm_error"] = None
        report["llm_model"] = resolved_model
    except (LLMConfigurationError, LLMRequestError) as exc:
        report["llm_narrative"] = None
        report["llm_error"] = str(exc)
        report["llm_model"] = None
    return report
