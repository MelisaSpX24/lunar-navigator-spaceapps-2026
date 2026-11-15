import pytest
from pydantic import ValidationError

from app.models.analysis import AnalysisRequest, AnalysisResult, BodySample, Decision, Score, Window


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok", "science_ready": False, "dem_ready": False,
        "kernels_ready": False, "reason_codes": ["SCIENCE_ENGINE_NOT_READY"]}


def test_valid_coordinates(request_data):
    request = AnalysisRequest.model_validate(request_data)
    assert request.site.latitude_deg == -89.468
    assert request.observer.surface_elevation_mode == "DEM"


def test_named_site_is_explicit(request_data, client):
    request_data["site"] = {"kind": "SITE_ID", "site_id": "CR1"}
    assert AnalysisRequest.model_validate(request_data).site.site_id == "CR1"
    result = client.post("/api/v1/analyses", json=request_data)
    assert result.status_code == 503
    assert result.json()["resolved_site"] is None


@pytest.mark.parametrize("field,value", [
    ("latitude_deg", -90), ("latitude_deg", 90), ("latitude_deg", -91),
    ("latitude_deg", 91), ("latitude_deg", None),
    ("longitude_deg_east", -1), ("longitude_deg_east", 360),
    ("longitude_deg_east", None), ("frame", "IAU_MOON"),
])
def test_invalid_coordinates(client, request_data, field, value):
    request_data["site"][field] = value
    response = client.post("/api/v1/analyses", json=request_data)
    assert response.status_code == 422
    assert response.json()["detail"]


@pytest.mark.parametrize("duration", [-1, 0, True, 1.5, "3600", 10**30])
def test_invalid_duration(client, request_data, duration):
    request_data["time"]["duration_s"] = duration
    assert client.post("/api/v1/analyses", json=request_data).status_code == 422


@pytest.mark.parametrize("timestamp", [
    "tomorrow", "2026-02-30T08:00:00Z", "2026-11-20T08:00:00",
    "2026-11-20", "2026-11-20T08:00:00+03:00", 1795161600,
])
def test_invalid_utc(client, request_data, timestamp):
    request_data["time"]["start_utc"] = timestamp
    assert client.post("/api/v1/analyses", json=request_data).status_code == 422


def test_invalid_profile(client, request_data):
    request_data["operation"]["profile"] = "CUSTOM"
    assert client.post("/api/v1/analyses", json=request_data).status_code == 422


@pytest.mark.parametrize("requirements", [
    {"min_earth_continuous_s": 21601}, {"min_sun_visible_s": 21601},
    {"require_simultaneous": True, "min_joint_continuous_s": 21601},
    {"min_joint_continuous_s": 100}, {"min_solar_disk_visible_fraction": 1.1},
    {"max_dark_gap_s": -1},
])
def test_inconsistent_requirements(client, request_data, requirements):
    request_data["operation"]["requirements"] = requirements
    assert client.post("/api/v1/analyses", json=request_data).status_code == 422


def test_engine_not_ready_has_no_scientific_results(client, request_data):
    response = client.post("/api/v1/analyses", json=request_data)
    assert response.status_code == 503
    result = response.json()
    assert result["execution_status"] == "NOT_RUN"
    assert result["decision"]["status"] == "INCOMPLETE"
    assert result["decision"]["reason_codes"] == ["SCIENCE_ENGINE_NOT_READY"]
    assert result["score"]["value"] is None
    assert result["series"] is None and result["horizons"] is None
    assert result["windows"] == {"sun": None, "earth": None, "joint": None}
    assert result["resolved_site"] is None and result["data_origin"] is None
    assert result["sources"] == []
    AnalysisResult.model_validate(result)


def test_execution_and_decision_are_independent(request_data):
    result = AnalysisResult(
        analysis_id="test-only", execution_status="COMPLETED",
        request=AnalysisRequest.model_validate(request_data),
        decision=Decision(status="INCOMPLETE", reason_codes=["INSUFFICIENT_DATA"]),
    )
    assert result.execution_status == "COMPLETED"
    assert result.decision.status == "INCOMPLETE"
    assert result.score.value is None


def test_zero_score_and_empty_windows_are_distinct_from_unknown():
    assert Score(value=0).model_dump()["value"] == 0
    assert Score().model_dump()["value"] is None


def test_output_constraints():
    with pytest.raises(ValidationError):
        BodySample(disk_visible_fraction=1.01)
    with pytest.raises(ValidationError):
        Score(value=101)
    with pytest.raises(ValidationError):
        Window(start_utc="2026-11-20T08:00:00Z", end_utc="2026-11-20T08:00:00Z",
               definition_id="test-only")


def test_separate_heights_and_reject_ambiguous_site(client, request_data):
    request_data["observer"] = {"solar_height_above_surface_m": 1,
                                "earth_height_above_surface_m": 3}
    assert client.post("/api/v1/analyses", json=request_data).status_code == 503
    request_data["site"]["site_id"] = "CR1"
    assert client.post("/api/v1/analyses", json=request_data).status_code == 422


def test_command_10_job_endpoints_are_exposed_with_unavailable_503(client):
    schema = client.get("/openapi.json").json()
    assert {"/api/v1/health", "/api/v1/analyses", "/api/v1/optimizations/temporal", "/api/v1/optimizations/local", "/api/v1/jobs/{job_id}"} <= set(schema["paths"])
    assert "503" in schema["paths"]["/api/v1/analyses"]["post"]["responses"]


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_nonfinite_model_values_rejected(request_data, value):
    request_data["site"]["latitude_deg"] = value
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate(request_data)
