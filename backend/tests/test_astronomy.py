"""Synthetic math and isolated SPICE integration; never NASA result fixtures."""
from contextlib import contextmanager
import json
import os
from pathlib import Path

import numpy as np
import pytest
import spiceypy as spice

from app.science.geometry import Observer, local_axes, observer_position_km, direction_angles
from app.science.kernels import FILES, LOCK, KernelSession, ScienceError, read_index
from app.science.astronomy import calculate, utc_to_et, et_to_utc
from app.data.manifest import sha256_file


def obs(**kwargs):
    return Observer(latitude_deg=-89.468,longitude_deg_east=222.6,surface_elevation_m=0,**kwargs)


def test_axes_and_surface_units():
    o=obs(device_height_m=2)
    axes=local_axes(o)
    np.testing.assert_allclose(axes@axes.T,np.eye(3),atol=1e-14)
    np.testing.assert_allclose(np.cross(axes[0],axes[1]),axes[2],atol=1e-14)
    assert np.linalg.norm(observer_position_km(o))==pytest.approx(1737.402)
    a=Observer(latitude_deg=0,longitude_deg_east=0,surface_elevation_m=100,device_height_m=2)
    np.testing.assert_allclose(observer_position_km(a),[1737.502,0,0])


@pytest.mark.parametrize("lat,lon",[(-90,0),(90,0),(-91,0),(0,360),(0,-1)])
def test_unsupported_coordinates(lat,lon):
    with pytest.raises(ValueError): Observer(latitude_deg=lat,longitude_deg_east=lon,surface_elevation_m=0)


@pytest.mark.parametrize("kwargs",[{"device_height_m":-1},{"surface_elevation_m":-1737400},{"surface_elevation_m":float("nan")}])
def test_invalid_heights(kwargs):
    with pytest.raises(ValueError): Observer(latitude_deg=0,longitude_deg_east=0,**kwargs)


@pytest.mark.parametrize("enu,az,el",[([0,1,0],0,0),([1,0,0],90,0),([0,-1,0],180,0),([-1,0,0],270,0),([0,0,1],None,90),([0,0,-1],None,-90)])
def test_compass_and_elevation(enu,az,el):
    o=obs()
    result=direction_angles(local_axes(o).T@np.array(enu),o)
    assert result[0]==pytest.approx(az) if az is not None else result[0] is None
    assert result[1]==pytest.approx(el)


def test_wrap_continuity_and_surface_parallax():
    a=Observer(latitude_deg=-89,longitude_deg_east=0,surface_elevation_m=0)
    b=Observer(latitude_deg=-89,longitude_deg_east=359.999999,surface_elevation_m=0)
    np.testing.assert_allclose(observer_position_km(a),observer_position_km(b),atol=1e-6)
    axes=local_axes(a)
    vals=[]
    for angle in [359.9,0.1]:
        vals.append(direction_angles(axes.T@np.array([np.sin(np.deg2rad(angle)),np.cos(np.deg2rad(angle)),0]),a)[0])
    assert abs((vals[1]-vals[0]+180)%360-180)==pytest.approx(.2)
    synthetic_target=np.array([10000.,20000.,30000.])
    centre=direction_angles(synthetic_target,a)
    surface=direction_angles(synthetic_target-observer_position_km(a),a)
    assert abs(surface[1]-centre[1])>.001


def test_kernel_mismatch_and_missing(tmp_path):
    index=tmp_path/"index.json"
    index.write_text(json.dumps({"files":[]}))
    with pytest.raises(ScienceError,match="PACKAGE_MISMATCH"): read_index(tmp_path,index)
    index.write_text(json.dumps({"files":[{"filename":n,"sha256":"a"*64} for n in FILES]}))
    with pytest.raises(ScienceError,match="KERNEL_MISSING"): read_index(tmp_path,index)
    assert spice.ktotal("ALL")==0
    with pytest.raises(ScienceError):
        with KernelSession(tmp_path,index): pass
    assert spice.ktotal("ALL")==0


def test_bad_kernel_and_hash(tmp_path):
    for n in FILES: (tmp_path/n).write_bytes(b"INVALID SYNTHETIC FILE")
    index=tmp_path/"index.json"
    records=[{"filename":n,"sha256":sha256_file(tmp_path/n)} for n in FILES]
    index.write_text(json.dumps({"files":records}))
    with pytest.raises(ScienceError,match="INVALID|TYPE_MISMATCH"): read_index(tmp_path,index)
    records[0]["sha256"]="a"*64
    index.write_text(json.dumps({"files":records}))
    with pytest.raises(ScienceError,match="HASH_MISMATCH"): read_index(tmp_path,index)


def test_load_failure_cleans_pool(monkeypatch,tmp_path):
    monkeypatch.setattr("app.science.kernels.read_index",lambda *args:[{"path":str(tmp_path/"absent.tf")}])
    with pytest.raises(ScienceError,match="KERNEL_LOAD_OR_COMPATIBILITY_ERROR"):
        with KernelSession(tmp_path,tmp_path/"index"): pass
    assert spice.ktotal("ALL")==0


@pytest.fixture
def synthetic_time_session(tmp_path):
    # Simplified TEST LSK, not NASA data or a historical leap-second table.
    path=tmp_path/"synthetic.tls"
    path.write_text("KPL/LSK\n\\begindata\nDELTET/DELTA_T_A = 32.184\nDELTET/K = 1.657D-3\nDELTET/EB = 1.671D-2\nDELTET/M = (6.239996, 1.99096871D-7)\nDELTET/DELTA_AT = (37, @2017-JAN-1)\n\\begintext\nSYNTHETIC TIME TEST ONLY\n")
    class Session:
        @contextmanager
        def call(self): yield
    with LOCK:
        assert spice.ktotal("ALL")==0
        spice.furnsh(str(path))
        try: yield Session()
        finally: spice.kclear()


def test_real_spice_time_conversion_with_synthetic_lsk(synthetic_time_session):
    s=synthetic_time_session
    t="2026-11-20T08:00:00Z"
    et=utc_to_et(s,t)
    assert et_to_utc(s,et)=="2026-11-20T08:00:00.000000Z"
    assert utc_to_et(s,"2026-11-20T08:00:01+00:00")-et==pytest.approx(1,abs=1e-6)


@pytest.mark.parametrize("time",["bad","2026-02-30T00:00:00Z","2026-11-20T08:00:00","2026-11-20T08:00:00+03:00"])
def test_time_rejected_before_spice(time):
    with pytest.raises(ValueError): utc_to_et(None,time)


def test_coverage_and_inactive_session():
    session=KernelSession("/missing","/missing")
    session.coverage={"synthetic":[[0.,10.]]}
    with pytest.raises(ScienceError,match="EPOCH_OUT"): session.check_epoch(11)
    with pytest.raises(ScienceError,match="INACTIVE"):
        with session.call(): pass


def test_session_load_cleanup_and_failure(monkeypatch):
    # Simulate package validation only; exercise real pool ownership/cleanup.
    import app.science.kernels as module
    monkeypatch.setattr(module,"read_index",lambda *args: [])
    monkeypatch.setattr(spice,"namfrm",lambda name:31007 if name=="MOON_ME_DE421" else 31006)
    monkeypatch.setattr(spice,"frinfo",lambda code:(301,2,31006))
    monkeypatch.setattr(spice,"bodvrd",lambda *args:(3,np.array([1737.4]*3)))
    monkeypatch.setattr(KernelSession,"_coverage",lambda self:{"test":[[0,1]]})
    with KernelSession("unused","unused") as session:
        assert session.active
    assert not session.active and spice.ktotal("ALL")==0
    with pytest.raises(RuntimeError,match="caller failure"):
        with KernelSession("unused","unused"):
            raise RuntimeError("caller failure")
    assert spice.ktotal("ALL")==0


def test_coverage_uses_pck_output_cell(monkeypatch):
    # Signature-checked fake, not a real NASA PCK coverage verification.
    from unittest.mock import create_autospec
    monkeypatch.setattr(spice,"spkobj",lambda path:[10,301,399])
    monkeypatch.setattr(spice,"spkcov",lambda *args:None)
    def fill(path,ids): spice.insrti(31006,ids)
    fake=create_autospec(spice.pckfrm,side_effect=fill)
    monkeypatch.setattr(spice,"pckfrm",fake)
    monkeypatch.setattr(spice,"pckcov",lambda *args:None)
    monkeypatch.setattr("app.science.kernels.intervals",lambda cell:[[0.,1.]])
    assert KernelSession("unused","unused")._coverage()["orientation"]==[[0.,1.]]
    assert fake.call_count==1


def test_spkcpo_receives_surface_observer(synthetic_time_session,monkeypatch):
    # Synthetic body vector validates wiring only, never actual Sun/Earth positions.
    s=synthetic_time_session
    s.check_epoch=lambda et:None
    s.records=[{"filename":"SYNTHETIC","sha256":"0"*64}]
    o=obs(device_height_m=2)
    calls=[]
    def fake(target,et,outref,refloc,abcorr,position,centre,obsref):
        calls.append((target,outref,refloc,abcorr,position,centre,obsref))
        return np.r_[local_axes(o).T@np.array([100.,100.,-50.]),np.zeros(3)],0
    monkeypatch.setattr(spice,"spkcpo",fake)
    result=calculate(s,o,"2026-11-20T08:00:00Z")
    assert result.sun.azimuth_deg==pytest.approx(45)
    assert result.earth.elevation_deg<0
    assert result.science_ready is False
    assert [c[0] for c in calls]==["SUN","EARTH"]
    for c in calls:
        assert (c[1],c[2],c[3],c[5],c[6])==("MOON_ME_DE421","OBSERVER","NONE","MOON","MOON_ME_DE421")
        np.testing.assert_allclose(c[4],observer_position_km(o))


def test_existing_pool_is_preserved(synthetic_time_session,tmp_path):
    count=spice.ktotal("ALL")
    with pytest.raises(ScienceError,match="POOL_IN_USE"):
        with KernelSession(tmp_path,tmp_path/"absent"): pass
    assert spice.ktotal("ALL")==count


@pytest.fixture
def real_session():
    directory=os.environ.get("NASA_KERNEL_DIR")
    index=os.environ.get("NASA_KERNEL_INDEX")
    if not directory or not index:
        pytest.skip("Real NASA kernels absent; astronomy/reference integration NOT_RUN")
    with KernelSession(directory,index) as session: yield session


def test_real_spice_sun_earth_and_reference(real_session):
    session=real_session
    o=obs(device_height_m=1)
    t="2026-11-20T08:00:00Z"
    result=calculate(session,o,t)
    assert 1.3e8 < result.sun.distance_km < 1.7e8
    assert 3e5 < result.earth.distance_km < 5e5
    et=utc_to_et(session,t)
    for target,direction in [("SUN",result.sun),("EARTH",result.earth)]:
        with session.call():
            azel,_=spice.azlcpo("ELLIPSOID",target,et,"NONE",False,True,
                                observer_position_km(o),"MOON","MOON_ME_DE421")
        assert azel[0]==pytest.approx(direction.distance_km,abs=1e-6)
        assert np.rad2deg(azel[1])%360==pytest.approx(direction.azimuth_deg,abs=1e-7)
        assert np.rad2deg(azel[2])==pytest.approx(direction.elevation_deg,abs=1e-7)


def test_real_libration_continuity_parallax_and_coverage(real_session):
    session=real_session
    first=calculate(session,obs(),"2026-11-20T08:00:00Z")
    second=calculate(session,obs(),"2026-11-20T08:01:00Z")
    later=calculate(session,obs(),"2026-11-27T08:00:00Z")
    assert abs(second.earth.elevation_deg-first.earth.elevation_deg)<.1
    assert abs(later.earth.elevation_deg-first.earth.elevation_deg)>1e-5
    et=utc_to_et(session,"2026-11-20T08:00:00Z")
    with session.call():
        centre,_=spice.spkpos("EARTH",et,"MOON_ME_DE421","NONE","MOON")
    assert abs(direction_angles(centre,obs())[1]-first.earth.elevation_deg)>1e-6
    with pytest.raises(ScienceError): calculate(session,obs(),"2200-01-01T00:00:00Z")
