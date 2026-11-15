"""Geodesic/slope/grid tests are analytic fixtures, not NASA safety evidence."""

from datetime import timedelta
import numpy as np
import pytest
from app.models.analysis import Coordinates
from app.optimization.local_site_models import LocalSiteOptimizationRequest
from app.optimization.local_site_optimizer import locations, slope_estimate, GEOD
from app.services.scientific_runner import template
from app.science.horizon_grid import build_grid
from app.science.visibility import VisibilityEngine
from test_visibility import fake, Session
from test_horizon import synthetic, req


@pytest.mark.parametrize(
    "lat,lon", [(-89.468, 222.6), (-89.9999, 359.99), (89.99, 0), (-45, 180)]
)
def test_geodesic_polar_radius_and_wrap(request_data, lat, lon):
    from app.models.analysis import AnalysisRequest

    request_data["site"].update(latitude_deg=lat, longitude_deg_east=lon)
    a = AnalysisRequest.model_validate(request_data)
    r = LocalSiteOptimizationRequest(
        baseline_analysis=a,
        window_template=template(a, "PROTOTYPE"),
        max_generated_candidates=24,
    )
    points = locations(r)
    assert points == locations(r) and len(points) < 24
    for loc in points:
        az, _, distance = GEOD.inv(lon, lat, loc.longitude_deg_east, loc.latitude_deg)
        assert 0 < distance <= 5000.000001 and 0 <= loc.longitude_deg_east < 360


@pytest.mark.parametrize("degrees", [0, 5, 10, 30])
def test_slope_real_pixel_scale(degrees):
    x = np.arange(3) * 5 * np.tan(np.radians(degrees))
    array = np.tile(x, (3, 1))
    assert slope_estimate(array, (5, 5)) == pytest.approx(degrees)
    assert (
        slope_estimate(np.ma.array(array, mask=np.eye(3, dtype=bool)), (5, 5)) is None
    )


def test_grid_exact_interpolated_unknown_and_wrap(tmp_path, fake):
    with synthetic(tmp_path) as h:
        e = VisibilityEngine(Session(), h.terrain)
        e.horizon = h
        grid = build_grid(e, req(max_range_m=100), 1, max_new_rays=2, max_samples=1000)
        assert not grid.complete_scheduled_grid
        assert grid.lookup(360) == grid.lookup(0)
        assert grid.lookup(0)["kind"] == "EXACT_GRID"
        assert grid.lookup(0.5)["kind"] == "APPROXIMATE_INTERPOLATION"
        assert grid.lookup(1.5)["kind"] == "UNKNOWN"
        assert not grid.lookup(0.5)["strict_visibility_evidence"]
        with pytest.raises(ValueError):
            grid.lookup(float("nan"))


def test_analysis_horizon_adapter_sorts_persisted_grid():
    import json
    from pathlib import Path
    from app.science.window_models import WindowSearchResult
    from app.services.scientific_runner import operation, adapt_analysis
    from app.science.horizon_grid import HorizonGrid
    from app.models.analysis import AnalysisRequest

    w = WindowSearchResult.model_validate(
        json.loads(Path("data_pipeline/evidence/command-07-windows.json").read_text())[
            "pilot"
        ]
    )
    a = AnalysisRequest.model_validate(
        {
            "site": {
                "kind": "COORDINATES",
                **w.request.visibility.terrain.location.model_dump(),
            },
            "time": {"start_utc": w.request.start_utc, "duration_s": 21600},
            "operation": {
                "profile": "SOLAR_POWERED_EXPERIMENT",
                "requirements": {"min_sun_visible_s": 3600},
            },
        }
    )
    grid = HorizonGrid(
        identity="synthetic-grid",
        source_signature="fixture",
        request=w.request.visibility.terrain,
        spacing_deg=1,
        observer_surface_elevation_m=0,
        elevations={"10.0": None, "0.0": None, "2.0": None},
        coverage={},
        complete_scheduled_grid=False,
        performance={},
        limitations=["TEST_FIXTURE"],
    )
    r = adapt_analysis(
        a,
        w,
        operation(a, w, "PROTOTYPE_SAMPLED_ESTIMATE"),
        "TEST_FIXTURE",
        "fixture",
        {"sun": grid},
    )
    assert [p.azimuth_deg for p in r.horizons[0].points] == [0, 2, 10]
    assert (
        not r.horizons[0].coverage_complete
        and r.series[0].sun.horizon_id == "synthetic-grid"
    )


@pytest.mark.parametrize(
    "baseline_gate,candidate_status,equivalent,expected",
    [
        (False, "MET", True, True),
        (False, "NOT_MET", True, False),
        (False, "MET", False, False),
    ],
)
def test_terrain_gate_and_mandatory_eligibility(
    baseline_gate, candidate_status, equivalent, expected
):
    from types import SimpleNamespace as NS
    from app.optimization.local_site_optimizer import improves_baseline

    baseline = NS(
        terrain={"eligible": baseline_gate}, operation=NS(decision=NS(status="MET"))
    )
    candidate = NS(
        terrain={"eligible": True},
        stage="DETAILED_EVALUATED",
        operation=NS(decision=NS(status=candidate_status)),
    )
    assert improves_baseline(baseline, candidate, equivalent, 0) == expected
