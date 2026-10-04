"""API smoke tests: the endpoints the UI uses, checked against answers from the brief."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def results_by_citation(address_id: str, as_of: str = "2026-10-01", **params) -> dict[str, str]:
    r = client.get("/api/lookup", params={"address_id": address_id, "as_of": as_of, **params})
    assert r.status_code == 200
    return {x["citation"]: x["result"] for x in r.json()["results"]}


def test_health():
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["rules"] == 60
    assert body["addresses"] >= 500


def test_lookup_answers_carry_disclaimer_and_as_of():
    body = client.get("/api/lookup", params={"address_id": "A0016", "as_of": "2026-10-01"}).json()
    assert body["as_of"] == "2026-10-01"
    assert "legal advice" in body["disclaimer"].lower()


def test_sf_local_rent_control_supersedes_state_cap():
    res = results_by_citation("A0016")
    assert res["S.F. Admin. Code § 37.3"] == "applies"
    assert res["Cal. Civ. Code § 1947.12"] == "superseded"


def test_california_algorithmic_ban_switches_on_jan_1_2026():
    assert results_by_citation("A0016", "2025-12-31")["Cal. Bus. & Prof. Code § 16729"] == "not_yet_effective"
    assert results_by_citation("A0016", "2026-01-02")["Cal. Bus. & Prof. Code § 16729"] == "applies"


def test_what_if_changes_only_the_answers_that_depend_on_the_fact():
    base = client.get("/api/lookup", params={"address_id": "A0005", "as_of": "2026-10-01"}).json()
    what_if = client.get("/api/lookup", params={"address_id": "A0005", "as_of": "2026-10-01", "year_built": 1960}).json()
    assert base["summary"].get("unknown", 0) > 0
    assert what_if["summary"].get("unknown", 0) < base["summary"]["unknown"]


def test_no_rent_cap_in_boston():
    body = client.get("/api/lookup", params={"address_id": "A0006", "as_of": "2026-10-01"}).json()
    caps = [x for x in body["results"] if x["category"] == "rent_increase_limits" and x["result"] == "applies"]
    assert caps == []


def test_change_cases():
    tests = client.get("/api/changes").json()
    assert len(tests) == 5
    assert all(t["check"]["matches"] for t in tests)


def test_open_questions_are_flagged_without_changing_answers():
    rules = {r["citation"]: r for r in client.get("/api/rules").json()["rules"]}
    berkeley = rules["Berkeley Mun. Code ch. 13.63"]
    assert berkeley["conflict_flag"] and berkeley["open_questions"]
    assert results_by_citation("A0005")["Berkeley Mun. Code ch. 13.63"] == "applies"
    assert rules["Cal. Civ. Code § 1950.6"]["open_questions"]
