import json
import os
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from rasterio.windows import Window

from app.data.manifest import Manifest, Product, sha256_file
from app.data.raster import (Limits, aligned, coverage, export_window, metadata,
                             projected_window, read_window, validate_lunar_crs)

ROOT = Path(__file__).resolve().parents[2]
LUNAR = "+proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +R=1737400 +units=m +no_defs"


@pytest.fixture
def product():
    return Product(id="SYNTHETIC", organization="TEST ONLY", family="synthetic",
                   source_url="synthetic:test", filename="test.tif", kind="ELEVATION",
                   frame="MOON_ME_DE421", units="m", version="test-1", limitations=["Not NASA data"])


def make_raster(path, data=None, crs=LUNAR, transform=None, unit="m", driver="GTiff"):
    if data is None:
        data = np.arange(100, dtype="float32").reshape(10, 10)
    with rasterio.open(path, "w", driver=driver, width=data.shape[1], height=data.shape[0],
                       count=1, dtype=data.dtype, crs=crs, transform=transform or from_origin(-100, 100, 20, 20), nodata=-9999) as ds:
        ds.write(data, 1)
        ds.set_band_unit(1, unit)
    return path


def test_metadata_window_and_provenance(tmp_path, product):
    path = make_raster(tmp_path / "test.tif")
    meta = metadata(path)
    assert meta["width"] == 10 and meta["resolution"] == [20, 20]
    assert meta["transform"] == [20, 0, -100, 0, -20, 100]
    data, report = read_window(path, product, Window(2, 3, 4, 2))
    assert data.shape == (2, 4) and data[0, 0] == 32
    assert report["product_version"] == "test-1" and report["product_id"] == "SYNTHETIC"
    assert report["science_ready"] is False


@pytest.mark.parametrize("window", [Window(-1,0,2,2), Window(9,9,2,2), Window(0,0,0,2), Window(.5,0,2,2)])
def test_outside_window(tmp_path, product, window):
    with pytest.raises(ValueError):
        read_window(make_raster(tmp_path/"a.tif"), product, window)


def test_missing_and_invalid_file(tmp_path, product):
    with pytest.raises(FileNotFoundError):
        metadata(tmp_path/"absent.tif")
    path = tmp_path/"bad.tif"
    path.write_text("not raster data")
    with pytest.raises(rasterio.errors.RasterioIOError):
        metadata(path)


def test_nodata_nan_inf_and_empty_valid(tmp_path, product):
    array = np.full((4,4), -9999, dtype="float32")
    array[0,:3] = [np.nan, np.inf, -np.inf]
    _, result = read_window(make_raster(tmp_path/"a.tif", array), product, Window(0,0,4,4))
    assert result["invalid_fraction"] == 1 and result["min"] is None


@pytest.mark.parametrize("crs", [None, "EPSG:4326", "EPSG:3031", "+proj=stere +lat_0=-90 +R=1737400 +units=km"])
def test_unsupported_crs(crs):
    with pytest.raises(ValueError):
        validate_lunar_crs(crs)


def test_layer_units_and_frame(tmp_path, product):
    path = make_raster(tmp_path/"a.tif")
    for changes in ({"kind":"SLOPE", "units":"deg"}, {"units":"feet"}, {"frame":"IAU_MOON"}):
        with pytest.raises(ValueError):
            read_window(path, product.model_copy(update=changes), Window(0,0,2,2))
    slope = make_raster(tmp_path/"s.tif", unit="deg")
    _, report = read_window(slope, product.model_copy(update={"kind":"SLOPE", "units":"deg"}), Window(0,0,2,2))
    assert report["units"] == "deg"


def test_alignment(tmp_path):
    a = make_raster(tmp_path/"a.tif")
    b = make_raster(tmp_path/"b.tif")
    c = make_raster(tmp_path/"c.tif", transform=from_origin(-90,100,20,20))
    assert aligned([a,b]) and not aligned([a,c])


def test_window_budget_and_bounded_read(tmp_path, product, monkeypatch):
    path = make_raster(tmp_path/"a.tif")
    with pytest.raises(ValueError, match="budget"):
        read_window(path, product, Window(0,0,10,10), Limits(max_pixels=4))
    # Fail if implementation ever falls back to a whole-band read.
    import app.data.raster as module
    original = module.open_local
    class Tracked:
        def __init__(self, ds): self.ds=ds
        def __getattr__(self, key): return getattr(self.ds,key)
        def __enter__(self): return self
        def __exit__(self,*args): self.ds.close()
        def read(self,*args,**kwargs):
            assert kwargs.get("window") == Window(0,0,2,2)
            return self.ds.read(*args,**kwargs)
    monkeypatch.setattr(module,"open_local",lambda p: Tracked(original(p)))
    assert read_window(path,product,Window(0,0,2,2))[0].size == 4


def test_cutout_mask_transform_hash_and_no_overwrite(tmp_path, product):
    source = make_raster(tmp_path/"source.tif")
    output = tmp_path/"cut.tif"
    result = export_window(source,product,Window(2,3,4,2),output)
    assert result["derived_file_sha256"] == sha256_file(output)
    assert metadata(output)["transform"] == [20,0,-60,0,-20,40]
    assert json.loads(output.with_suffix(".tif.json").read_text())["source"]["id"] == "SYNTHETIC"
    with pytest.raises(ValueError): export_window(source,product,Window(0,0,2,2),output)


def test_projected_coverage_is_not_quality_claim(tmp_path, product):
    path = make_raster(tmp_path/"a.tif")
    assert projected_window(path,0,0,20) == Window(4,4,2,2)
    report = coverage(path,product,-90,0,radii=(20,3000))
    assert report["point_inside"]
    assert report["areas"][0]["bounding_square_inside"]
    assert not report["areas"][1]["bounding_square_inside"]
    assert report["areas"][0]["valid_data_coverage"] == "NOT_CHECKED"


@pytest.mark.parametrize("name,count", [("lola.json",12),("kernels.json",5)])
def test_real_source_manifests_not_ready(name,count):
    manifest = Manifest.model_validate_json((ROOT/"data_pipeline/manifests"/name).read_text())
    assert len(manifest.products) == count and not manifest.science_ready
    assert all(p.sha256 is None and p.local_path is None and p.status != "READY" for p in manifest.products)


def test_missing_kernel_cannot_be_ready(product):
    values=product.model_dump()
    values.update(kind="SPK", status="READY",local_path="/absent/de421.bsp")
    with pytest.raises(ValueError): Product.model_validate(values)
    values.update(status="UNVERIFIED",local_path=None,sha256="a"*64)
    with pytest.raises(ValueError): Product.model_validate(values)


def test_missing_quality_reference(product):
    with pytest.raises(ValueError):
        Manifest(schema_version="1.0",science_ready=False,access_notes=[],products=[product.model_copy(update={"quality_layer_ids":["absent"]})])


def test_local_cog_and_masked_export(tmp_path,product):
    from rasterio.shutil import copy
    data=np.ones((32,32),dtype="float32")
    data[0,0]=-9999
    src=make_raster(tmp_path/"src.tif",data)
    cog=tmp_path/"cog.tif"
    copy(src,cog,driver="COG",blocksize=128)
    values,_=read_window(cog,product,Window(0,0,2,2))
    assert values.mask[0,0]
    out=tmp_path/"derived.tif"
    export_window(cog,product,Window(0,0,2,2),out)
    assert read_window(out,product,Window(0,0,2,2))[0].mask[0,0]


def test_cli_and_range_ignored_never_consumes_body(monkeypatch):
    import sys
    sys.path.insert(0,str(ROOT))
    from data_pipeline.cli import probe_range
    class Response:
        status=200
        headers={}
        url="https://pgda.gsfc.nasa.gov/test.tif"
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self,*args): raise AssertionError("Must not consume ignored Range response")
    monkeypatch.setattr("data_pipeline.cli.urlopen",lambda *a,**k:Response())
    assert probe_range(Response.url)["body_bytes_read"]==0
    with pytest.raises(ValueError): probe_range("https://example.com/test.tif")


def test_limits_and_manifest_hash(tmp_path,product):
    with pytest.raises(ValueError): Limits(max_pixels=0)
    path=tmp_path/"kernel"
    path.write_bytes(b"synthetic")
    values=product.model_dump()
    values.update(local_path=str(path),sha256="a"*64,status="FILE_INSPECTED")
    with pytest.raises(ValueError): Product.model_validate(values)


@pytest.mark.parametrize("variable,product_id", [("NASA_SITE01_DEM","Site01_final_adj_5mpp_surf.tif"),("NASA_PRODUCT90_DEM","LDEM_80S_20MPP_ADJ.TIF")])
def test_optional_real_file(variable,product_id):
    path=os.environ.get(variable)
    if not path:
        pytest.skip(f"{variable} absent: real NASA raster integration NOT_RUN")
    manifest=Manifest.model_validate_json((ROOT/"data_pipeline/manifests/lola.json").read_text())
    product=next(p for p in manifest.products if p.id==product_id)
    _, result=read_window(path,product,Window(0,0,1,1))
    assert result["product_id"]==product_id
