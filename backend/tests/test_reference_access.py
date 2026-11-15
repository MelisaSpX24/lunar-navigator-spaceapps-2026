"""Offline acquisition guard tests. These do not validate NASA data."""
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from data_pipeline.reference_access import horizons_plan, save_bounded, NoRedirect


def test_reference_plan_has_six_explicit_surface_queries():
    plan=horizons_plan()
    assert plan["comparison_status"]=="NOT_VERIFIED" and plan["status"]=="NOT_RUN"
    assert len(plan["queries"])==6
    for q in plan["queries"]:
        params=parse_qs(urlparse(q["url"]).query)
        assert params["CENTER"]==["'coord@301'"]
        assert params["SITE_COORD"]==["'222.6,-89.468,0.001'"]
        assert params["QUANTITIES"]==["'4,20'"]
        assert params["COMMAND"][0] in ("'10'","'399'")
        assert params["RANGE_UNITS"]==["'KM'"]


class Response:
    url="https://naif.jpl.nasa.gov/test"
    def __init__(self,size): self.headers={"Content-Length":str(size)}
    def __enter__(self): return self
    def __exit__(self,*args): pass


@pytest.mark.parametrize("size",[None,1000])
def test_no_get_if_size_unknown_or_over_budget(monkeypatch,tmp_path,size):
    calls=[]
    def fake(req,timeout):
        calls.append(req.get_method())
        obj=Response(size)
        if size is None: obj.headers={}
        return obj
    monkeypatch.setattr("data_pipeline.reference_access.urlopen",fake)
    with pytest.raises(ValueError): save_bounded(Response.url,tmp_path/"k",100,"test")
    assert calls==["HEAD"] and not (tmp_path/"k").exists()


def test_bounded_get_and_hash_input_preservation(monkeypatch,tmp_path):
    class Body(Response):
        def __init__(self): super().__init__(3); self.sent=False
        def read(self,size):
            if self.sent: return b""
            self.sent=True
            return b"abc"
    monkeypatch.setattr("data_pipeline.reference_access.urlopen",lambda req,timeout:Response(3) if req.get_method()=="HEAD" else Body())
    path=tmp_path/"kernel"
    assert save_bounded(Response.url,path,10,"test")==3
    assert path.read_bytes()==b"abc"
    with pytest.raises(FileExistsError): save_bounded(Response.url,path,10,"test")
    assert path.read_bytes()==b"abc"


def test_redirect_rejected_without_following():
    assert NoRedirect().redirect_request(None,None,302,"",{},"https://example.com/") is None


def test_size_mismatch_removes_partial(monkeypatch,tmp_path):
    class Body(Response):
        def read(self,size): return b""
    monkeypatch.setattr("data_pipeline.reference_access.urlopen",lambda req,timeout:Body(3))
    with pytest.raises(ValueError): save_bounded(Response.url,tmp_path/"k",10,"test")
    assert list(tmp_path.iterdir())==[]
