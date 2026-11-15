import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    with TestClient(create_app()) as instance:
        yield instance


@pytest.fixture
def request_data():
    # Scenario inputs only. No DEM coverage or scientific results are asserted.
    return {
        "site": {"kind": "COORDINATES", "latitude_deg": -89.468,
                 "longitude_deg_east": 222.6},
        "time": {"start_utc": "2026-11-20T08:00:00Z", "duration_s": 21600},
        "operation": {"profile": "CUSTOM_OPERATION", "requirements": {
            "min_earth_continuous_s": 3600}},
    }
