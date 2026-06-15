from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from analysis.pattern_inspector import inspect_patterns
from analysis.pattern_inspector_llm import (
    attach_llm_narrative,
    build_llm_context,
    generate_llm_narrative,
)
from analysis.tests.test_pattern_inspector import _sample_frame


def test_build_llm_context_excludes_raw_samples() -> None:
    report = inspect_patterns(_sample_frame())
    context = build_llm_context(report)
    assert "patterns" in context
    assert "samples" not in json.dumps(context)


def test_attach_llm_narrative_without_api_key() -> None:
    report = inspect_patterns(_sample_frame())
    enriched = attach_llm_narrative(report, enabled=True, api_key="")
    assert enriched["llm_narrative"] is None
    assert "OPENAI_API_KEY" in str(enriched["llm_error"])


def test_generate_llm_narrative_parses_response() -> None:
    report = inspect_patterns(_sample_frame())
    fake_response = {
        "choices": [
            {
                "message": {
                    "content": "Your low-rated swings share rushed transitions and higher wrist return."
                }
            }
        ]
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(fake_response).encode("utf-8")

    with patch("analysis.pattern_inspector_llm.urllib.request.urlopen", return_value=FakeResponse()):
        narrative = generate_llm_narrative(report, api_key="test-key", model="gpt-4o-mini")

    assert "rushed transitions" in narrative


def test_inspect_patterns_include_llm_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_generate(report, **kwargs):
        return "Practice swings show rushed transition in low-rated cohort."

    monkeypatch.setattr(
        "analysis.pattern_inspector.attach_llm_narrative",
        lambda report, enabled=True, api_key=None, model=None, base_url=None: {
            **report,
            "llm_narrative": fake_generate(report) if enabled else None,
            "llm_error": None,
            "llm_model": "gpt-4o-mini",
        },
    )

    report = inspect_patterns(_sample_frame(), include_llm=True)
    assert report["llm_narrative"] is not None
