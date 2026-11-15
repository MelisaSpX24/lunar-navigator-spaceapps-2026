"""CLI validates inputs and never recomputes NASA geometry."""

import json, sys
import pytest
from data_pipeline.operations_cli import main
from test_operations import windows, operation


def test_cli_json_overwrite_and_invalid_request(tmp_path, windows, monkeypatch):
    q = operation(windows, {"min_earth_continuous_s": 3600})
    req = tmp_path / "request.json"
    src = tmp_path / "windows.json"
    out = tmp_path / "output.json"
    req.write_text(q.model_dump_json(exclude_unset=True))
    src.write_text(windows.model_dump_json())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "operations",
            "--request",
            str(req),
            "--windows",
            str(src),
            "--output",
            str(out),
        ],
    )
    main()
    r = json.loads(out.read_text())
    assert r["decision"]["status"] == "MET"
    with pytest.raises(SystemExit):
        main()
    original = out.read_bytes()
    req.write_text("{}")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "operations",
            "--request",
            str(req),
            "--windows",
            str(src),
            "--output",
            str(tmp_path / "bad.json"),
        ],
    )
    with pytest.raises(ValueError):
        main()
    assert not (tmp_path / "bad.json").exists() and out.read_bytes() == original
