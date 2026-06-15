from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from analysis.web_api.main import create_app


def _write_fixture_csv(path):
    path.write_text(
        "\n".join(
            [
                "id,date,rating,club,tempo_ratio,peak_rotational_velocity,swing_plane_stability,sample_count",
                "a,2026-06-10T10:00:00Z,4,7i,0.8,1.5,0.9,120",
                "b,2026-06-11T10:00:00Z,5,Driver,1.0,2.1,0.85,135",
            ]
        ),
        encoding="utf-8",
    )


def test_health_endpoint(tmp_path):
    csv_path = tmp_path / "features.csv"
    _write_fixture_csv(csv_path)
    client = TestClient(create_app(features_path=str(csv_path)))

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_summary_endpoint_with_filters(tmp_path):
    csv_path = tmp_path / "features.csv"
    _write_fixture_csv(csv_path)
    client = TestClient(create_app(features_path=str(csv_path)))

    response = client.get("/summary", params={"clubs": "Driver"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["swings"] == 1
    assert payload["avg_rating"] == 5.0
    assert payload["avg_tempo_ratio"] == 1.0


def test_records_endpoint_respects_limit(tmp_path):
    csv_path = tmp_path / "features.csv"
    _write_fixture_csv(csv_path)
    client = TestClient(create_app(features_path=str(csv_path)))

    response = client.get("/records", params={"limit": 1})
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert len(payload["items"]) == 1


def test_api_key_protects_data_endpoints(tmp_path):
    csv_path = tmp_path / "features.csv"
    _write_fixture_csv(csv_path)
    client = TestClient(create_app(features_path=str(csv_path), api_key="secret"))

    unauthorized = client.get("/summary")
    assert unauthorized.status_code == 401

    authorized = client.get("/summary", headers={"X-API-Key": "secret"})
    assert authorized.status_code == 200


def test_patterns_endpoint(tmp_path):
    csv_path = tmp_path / "features.csv"
    _write_fixture_csv(csv_path)
    client = TestClient(create_app(features_path=str(csv_path)))

    response = client.get("/patterns")
    assert response.status_code == 200
    payload = response.json()
    assert payload["swing_count"] == 2
    assert "patterns" in payload
    assert "markdown" in payload
    assert payload.get("llm_narrative") is None


def test_patterns_endpoint_llm_without_api_key(tmp_path):
    csv_path = tmp_path / "features.csv"
    _write_fixture_csv(csv_path)
    client = TestClient(create_app(features_path=str(csv_path)))

    response = client.get("/patterns", params={"llm": "true"})
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("llm_narrative") is None
    assert payload.get("llm_error")


def test_movement_endpoints(tmp_path):
    csv_path = tmp_path / "features.csv"
    raw_path = tmp_path / "swings.json"
    _write_fixture_csv(csv_path)
    raw_path.write_text(
        (
            Path(__file__).resolve().parents[2]
            / "tests"
            / "fixtures"
            / "test_swings.json"
        ).read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    client = TestClient(
        create_app(features_path=str(csv_path), raw_swings_path=str(raw_path))
    )

    swings = client.get("/movement/swings")
    assert swings.status_code == 200
    swing_items = swings.json()["items"]
    assert len(swing_items) == 1

    swing_id = swing_items[0]["id"]
    detail = client.get(f"/movement/{swing_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["sample_count"] == 6
    assert len(payload["series"]["times"]) == 6
    assert len(payload["event_markers"]) == 3
    assert len(payload["phase_markers"]) >= 5
    assert payload["swing_mode"] in {"practice", "full"}
    assert isinstance(payload["fault_flags"], list)
    assert payload["recommendations"] == [
        "Keep your tempo smooth through impact.",
        "Maintain posture during follow-through.",
    ]
    assert payload["follow_through"] is not None
    assert payload["follow_through"]["rotation_deg"] > 0
    assert len(payload["follow_through"]["path"]["times"]) >= 1
