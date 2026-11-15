"""Synthetic associated quality rasters and observer preparation; not NASA data."""
import json

import numpy as np
import pytest
from pydantic import ValidationError
import rasterio
from rasterio.transform import from_origin
from rasterio.windows import Window

from app.data.dem import open_dem
from app.data.dem_models import DemReference, DemSample
from app.data.errors import DemError
from app.data.lola import lola_reference
from app.data.manifest import Product, Manifest, sha256_file
from app.data.observer import prepare_observer
from app.data.quality import QualityLayer, read_quality_window, sample_quality_layers
from app.science.geometry import observer_position_km
from test_dem import ROOT, LUNAR, raster, reference, location, sample, disk


def quality(tmp_path, kind="COUNT", value=4, *, transform=None, unit=None, family="synthetic", frame="MOON_ME_DE421", crs=LUNAR):
    path = raster(tmp_path/f"{kind}.tif", np.full((10, 10), value, dtype="float32"),
                  transform=transform or from_origin(-50, 50, 10, 10), crs=crs)
    product = Product(id=kind, organization="SYNTHETIC ONLY", family=family,
                      source_url="synthetic:quality", filename=path.name, kind=kind,
                      version="test-1", units=unit or ("count" if kind == "COUNT" else "deg" if kind == "SLOPE" else "m"),
                      frame=frame, limitations=["Not NASA data"])
    return QualityLayer(path=path, product=product, sha256=sha256_file(path))


def elevation(tmp_path):
    path = raster(tmp_path/"elevation.tif")
    return path, reference(path, source_product_family="synthetic", quality_layer_ids=("COUNT", "SLOPE", "HEIGHT_ERROR", "EFFECTIVE_RESOLUTION"))


def test_associated_layers_keep_identity_units_and_no_confidence_score(tmp_path):
    path, ref = elevation(tmp_path)
    layers = [quality(tmp_path, "COUNT", 1000), quality(tmp_path, "SLOPE", 2),
              quality(tmp_path, "HEIGHT_ERROR", 3), quality(tmp_path, "EFFECTIVE_RESOLUTION", 5)]
    with open_dem(path, ref) as dem:
        result = dem.sample(location(), allow_unverified_registration=True, quality_layers=layers)
    assert result.surface_elevation_m == 12.5
    assert result.quality.status == "QUALITY_LAYERS_PRESENT"
    assert [r.value for r in result.quality.layers] == [1000, 2, 3, 5]
    assert [r.units for r in result.quality.layers] == ["count", "deg", "m", "m"]
    assert all(r.sha256 == l.sha256 for r, l in zip(result.quality.layers, layers))
    assert all(r.organization == "SYNTHETIC ONLY" for r in result.quality.layers)
    assert "no confidence score" in result.quality.interpretation
    assert "score" not in result.model_dump()
    assert result.frame_status == "PROVISIONAL"


@pytest.mark.parametrize("kind,value", [("COUNT", -1), ("COUNT", 1.5), ("SLOPE", 91),
    ("HEIGHT_ERROR", -1), ("EFFECTIVE_RESOLUTION", -1), ("COUNT", -9999), ("COUNT", float('nan'))])
def test_quality_masks_do_not_invalidate_otherwise_valid_elevation(tmp_path, kind, value):
    path, ref = elevation(tmp_path)
    with open_dem(path, ref) as dem:
        result = dem.sample(location(), allow_unverified_registration=True,
                            quality_layers=[quality(tmp_path, kind, value)])
    assert result.status == "VALID" and result.surface_elevation_m == 12.5
    assert result.quality.status == "PARTIAL_QUALITY_DATA"
    assert result.quality.layers[0].value is None
    assert result.quality.layers[0].status == "INVALID_NODATA"
    json.dumps(result.model_dump(mode="json"), allow_nan=False)


@pytest.mark.parametrize("case", ["grid", "crs", "unit", "frame", "family", "hash", "association", "duplicate"])
def test_quality_never_silently_uses_unrelated_or_misaligned_pixels(tmp_path, case):
    path, ref = elevation(tmp_path)
    kwargs = {"transform": from_origin(-49, 50, 10, 10)} if case == "grid" else {}
    if case == "unit": kwargs["unit"] = "m"
    if case == "crs": kwargs["crs"] = "EPSG:3031"
    if case == "frame": kwargs["frame"] = "IAU_MOON"
    if case == "family": kwargs["family"] = "other"
    layer = quality(tmp_path, **kwargs)
    if case == "hash": layer = layer.model_copy(update={"sha256": "0"*64})
    if case == "association": ref = ref.model_copy(update={"quality_layer_ids": ()})
    with open_dem(path, ref) as dem:
        with pytest.raises(DemError):
            sample_quality_layers(dem, sample(dem), [layer, layer] if case == "duplicate" else [layer])


def test_quality_window_is_bounded_and_absence_is_not_zero(tmp_path):
    path, ref = elevation(tmp_path)
    with open_dem(path, ref) as dem:
        absent = sample_quality_layers(dem, sample(dem), [])
        values, evidence = read_quality_window(dem, quality(tmp_path), Window(1, 2, 2, 3))
        heights, height_evidence = dem.read_elevation_window(Window(1, 2, 2, 3))
    assert absent.status == "QUALITY_NOT_ASSESSED" and absent.layers == []
    assert values.shape == heights.shape == (3, 2)
    assert evidence["source"]["id"] == "COUNT"
    assert evidence["source_frame_evidence"] == "MANIFEST_DECLARATION_NOT_PRODUCT_VERIFIED"
    assert height_evidence["reference"]["raster_sha256"] == ref.raster_sha256


def test_quality_external_mask_and_hash_once_per_immutable_session(tmp_path, monkeypatch):
    import app.data.quality as module
    path, ref = elevation(tmp_path)
    layer = quality(tmp_path)
    mask = np.full((10, 10), 255, dtype="uint8"); mask[5, 5] = 0
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
        with rasterio.open(layer.path, "r+") as ds: ds.write_mask(mask)
    layer = layer.model_copy(update={"sha256": sha256_file(layer.path)})
    calls = []
    original = module.sha256_file
    def counted(p):
        calls.append(p)
        return original(p)
    monkeypatch.setattr(module, "sha256_file", counted)
    with open_dem(path, ref) as dem:
        result = dem.sample(location(), allow_unverified_registration=True, quality_layers=[layer])
        values, _ = read_quality_window(dem, layer, Window(0, 0, 2, 2))
    assert result.surface_elevation_m == 12.5
    assert result.quality.layers[0].value is None and result.quality.status == "PARTIAL_QUALITY_DATA"
    assert values.count() == 4 and len(calls) == 1


@pytest.mark.parametrize("internal", [True, False])
def test_internal_external_mask_and_auxiliary_provenance(tmp_path, internal):
    path = raster(tmp_path/"masked.tif")
    mask = np.full((10, 10), 255, dtype="uint8"); mask[5, 5] = 0
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=internal):
        with rasterio.open(path, "r+") as ds: ds.write_mask(mask)
    with open_dem(path, reference(path)) as dem:
        result = sample(dem)
        assert disk(dem).fractions()["valid_height_fraction"] < 1
    assert result.status == "NODATA" and result.surface_elevation_m is None
    if not internal:
        assert result.auxiliary_file_hashes[path.name+".msk"] == sha256_file(path.with_suffix('.tif.msk'))


def test_observer_keeps_surface_device_metres_and_provisional_frame(tmp_path):
    path = raster(tmp_path/"test.tif", np.full((10, 10), 1944.14, dtype="float32"))
    with open_dem(path, reference(path)) as dem: result = sample(dem)
    prepared = prepare_observer(result, device_height_m=2)
    assert prepared.observer.surface_elevation_m == result.surface_elevation_m
    assert prepared.observer.device_height_m == 2
    assert np.linalg.norm(observer_position_km(prepared.observer)) == pytest.approx((1737400+result.surface_elevation_m+2)/1000)
    assert prepared.observer.height_datum == "ASSUMED_REFERENCE_SPHERE"
    assert prepared.frame_status == "PROVISIONAL" and not prepared.science_ready
    assert "FRAME_NOT_PRODUCT_VERIFIED" in prepared.reason_codes
    assert prepared.dem_sample.reference.absolute_vertical_error_m is None
    with pytest.raises(ValidationError): prepare_observer(result, device_height_m=-1)


def test_no_observer_from_nodata_or_unsupported_frame(tmp_path):
    path = raster(tmp_path/"test.tif", np.full((10, 10), -9999, dtype="float32"))
    with open_dem(path, reference(path)) as dem: result = sample(dem)
    with pytest.raises(DemError, match="INVALID_DEM_OBSERVER"): prepare_observer(result, 1)
    incompatible = reference(path, declared_source_frame="IAU_MOON", source_frame_evidence="INCOMPATIBLE")
    with open_dem(path, incompatible) as dem:
        with pytest.raises(DemError, match="INCOMPATIBLE_FRAME"): sample(dem)


@pytest.mark.parametrize("field", ["declared_lunar_radius_m", "vertical_unit", "vertical_reference", "vertical_evidence", "product_version"])
def test_missing_reference_fields_are_not_inferred(tmp_path, field):
    path = raster(tmp_path/"test.tif")
    values = reference(path).model_dump()
    values.pop(field)
    with pytest.raises(ValidationError): DemReference(**values)


def test_reference_round_trip_and_wrong_frame_declaration(tmp_path):
    path = raster(tmp_path/"test.tif")
    ref = reference(path)
    assert DemReference.model_validate_json(ref.model_dump_json()) == ref
    with pytest.raises(ValidationError): reference(path, declared_source_frame="MOON_PA_DE421")


def test_sample_cannot_promote_its_reference_or_hide_registration_assumption(tmp_path):
    path = raster(tmp_path/"test.tif")
    with open_dem(path, reference(path)) as dem: result = sample(dem)
    values = result.model_dump()
    values["frame_status"] = "PRODUCT_SPECIFIC_VERIFIED"
    with pytest.raises(ValidationError): DemSample(**values)
    values = result.model_dump()
    values["prototype_registration_assumption_used"] = False
    with pytest.raises(ValidationError): DemSample(**values)


def test_page_only_lola_manifest_stays_unready_and_is_not_lroc(tmp_path):
    manifest = Manifest.model_validate_json((ROOT/"data_pipeline/manifests/lola.json").read_text())
    product = next(p for p in manifest.products if p.kind == "ELEVATION")
    with pytest.raises(DemError, match="UNKNOWN_VERTICAL_DATUM"):
        lola_reference(tmp_path/product.filename, product, vertical_evidence="")
    assert not manifest.science_ready and product.status == "PAGE_DOCUMENTED"
    path = raster(tmp_path/product.filename)
    documented = product.model_copy(update={"height_datum": "HEIGHT_ABOVE_REFERENCE_SPHERE", "version": "SYNTHETIC_TEST_ONLY"})
    ref = lola_reference(path, documented, vertical_evidence="SYNTHETIC TEST DECLARATION; NOT A REAL LOLA VERIFICATION")
    assert ref.family == "LOLA" and ref.frame_status == "PROVISIONAL"
    assert not ref.product_specific_frame_verified
    assert ref.quality_layer_ids == tuple(product.quality_layer_ids)
    with pytest.raises(DemError, match="WRONG_PRODUCT_FAMILY"):
        lola_reference(path, documented.model_copy(update={"family": "LROC"}), vertical_evidence="test")


def test_bad_raster_returns_controlled_error(tmp_path):
    path = tmp_path/"wrong.tif"; path.write_text('<html>not a raster</html>')
    with pytest.raises(DemError, match="INVALID_RASTER"):
        with open_dem(path, reference(path)): pass


def test_quality_handles_reused_closed_and_metadata_rechecked(tmp_path, monkeypatch):
    import app.data.quality as module
    path, ref = elevation(tmp_path)
    layer = quality(tmp_path)
    opened=[]
    original=module.open_local
    def tracked(p):
        ds=original(p);opened.append(ds);return ds
    monkeypatch.setattr(module,'open_local',tracked)
    with open_dem(path,ref) as dem:
        for _ in range(3):read_quality_window(dem,layer,Window(0,0,1,1))
        assert len(opened)==1 and not opened[0].closed
        bad=layer.model_copy(update={'product':layer.product.model_copy(update={'units':'m'})})
        with pytest.raises(DemError):read_quality_window(dem,bad,Window(0,0,1,1))
        assert len(opened)==2 and opened[1].closed
    assert all(ds.closed for ds in opened)
