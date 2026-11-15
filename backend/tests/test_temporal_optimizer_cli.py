"""Recorded CLI rejects invalid inputs and preserves output files."""

import sys, json
import pytest
from test_temporal_optimizer import config
from data_pipeline.temporal_optimizer_cli import main


def test_recorded_cli(tmp_path, config, monkeypatch):
    req = tmp_path / "request.json"
    out = tmp_path / "output.json"
    req.write_text(config.model_dump_json(exclude_unset=True))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "optimizer",
            "--request",
            str(req),
            "--output",
            str(out),
            "--recorded",
            "data_pipeline/evidence/command-07-windows.json",
        ],
    )
    main()
    r = json.loads(out.read_text())
    assert r["baseline"]["evidence_mode"] == "RECORDED" and not r["science_ready"]
    with pytest.raises(SystemExit):
        main()
    assert json.loads(out.read_text()) == r


@pytest.mark.parametrize("bad", ["{}", '{"search_start_utc":NaN}', "not json"])
def test_invalid_cli(tmp_path, monkeypatch, bad):
    req = tmp_path / "request.json"
    out = tmp_path / "output.json"
    req.write_text(bad)
    monkeypatch.setattr(
        sys, "argv", ["optimizer", "--request", str(req), "--output", str(out)]
    )
    with pytest.raises(ValueError):
        main()
    assert not out.exists()
