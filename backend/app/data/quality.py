"""Associated quality layers on the exact source grid; no confidence scoring."""
from pathlib import Path

import numpy as np
from rasterio.windows import Window

from app.data.dem_models import QualityAssessment, QualitySample, SHA256
from app.data.errors import DemError
from app.data.manifest import Product, sha256_file
from app.data.raster import open_local, check_layer, read_dataset_window
from app.models.analysis import Model


class QualityLayer(Model):
    path: Path
    product: Product
    sha256: SHA256


def read_quality_window(dem, layer: QualityLayer, window: Window):
    """Return independently masked values, preserving the existing LOLA checks.

    Exact grid equality is necessary, not evidence of geodetic registration.
    Association must be explicit in the DEM reference, never inferred by shape.
    """
    product = layer.product
    if product.kind not in ("COUNT", "HEIGHT_ERROR", "SLOPE", "EFFECTIVE_RESOLUTION"):
        raise DemError("UNSUPPORTED_QUALITY_LAYER", "Expected count, height error, slope or effective resolution")
    if product.id not in dem.reference.quality_layer_ids or product.family != dem.reference.source_product_family:
        raise DemError("QUALITY_SOURCE_MISMATCH", "Layer is not an associated product in this DEM source family")
    key = (layer.path.resolve(), layer.sha256, product.sha256)
    digest = dem._quality_hashes.get(key)
    if digest is None:
        digest = sha256_file(layer.path)
        if digest != layer.sha256 or (product.sha256 is not None and digest != product.sha256):
            raise DemError("SOURCE_HASH_MISMATCH", "Quality layer hash does not match its declared identity")
        dem._quality_hashes[key] = digest
    # Metadata/identity checked once per immutable session, with bounded handles.
    reader_key = (key, product.model_dump_json())
    ds = dem._quality_readers.get(reader_key)
    if ds is None:
        ds = open_local(layer.path)
        try:
            check_layer(ds, product)
            if (ds.crs, ds.transform, ds.width, ds.height) != (dem.ds.crs, dem.ds.transform, dem.ds.width, dem.ds.height):
                raise DemError("MISALIGNED_QUALITY_GRID", "Quality CRS/affine/dimensions differ; no implicit resampling")
        except ValueError as exc:
            ds.close()
            if isinstance(exc, DemError):
                raise
            raise DemError("INVALID_QUALITY_METADATA", str(exc)) from exc
        except Exception:
            ds.close()
            raise
        if len(dem._quality_readers) >= 8:
            _, old = dem._quality_readers.popitem(last=False)
            old.close()
        dem._quality_readers[reader_key] = ds
    dem._quality_readers.move_to_end(reader_key)
    try:
        values, report = read_dataset_window(ds, product, window, dem.limits)
    except ValueError as exc:
        raise DemError("INVALID_QUALITY_METADATA", str(exc)) from exc
    if product.kind == "COUNT":
        # A fractional number cannot represent a count of observations.
        values = np.ma.array(values.data, mask=np.ma.getmaskarray(values) | (values.data != np.floor(values.data)))
    valid = values.compressed()
    report.update(valid_pixels=int(valid.size), invalid_fraction=float(np.ma.getmaskarray(values).mean()),
                  min=float(valid.min()) if valid.size else None, max=float(valid.max()) if valid.size else None)
    report.update(source_file_sha256=digest, source=product.model_dump(mode="json"),
                  source_frame_evidence="MANIFEST_DECLARATION_NOT_PRODUCT_VERIFIED",
                  interpretation="Measurement only; not a confidence score or landing hazard.")
    return values, report


def sample_quality_layers(dem, sample, layers: list[QualityLayer]) -> QualityAssessment:
    """Quality at the same declared cell; no coverage-wide quality claim."""
    if sample.raster_sha256 != dem.reference.raster_sha256:
        raise DemError("QUALITY_SOURCE_MISMATCH", "Elevation sample belongs to a different raster")
    if len({layer.product.id for layer in layers}) != len(layers):
        raise DemError("DUPLICATE_QUALITY_LAYER", "Each quality product must be listed once")
    results = []
    for layer in layers:
        if sample.status == "OUTSIDE_RASTER":
            raise DemError("OUT_OF_RASTER_BOUNDS", "No corresponding quality cell outside the elevation raster")
        values, report = read_quality_window(dem, layer, Window(sample.column_zero_based, sample.row_zero_based, 1, 1))
        valid = not bool(np.ma.getmaskarray(values)[0, 0])
        product = layer.product
        results.append(QualitySample(
            product_id=product.id, product_version=product.version, organization=product.organization,
            family=product.family, source_url=product.source_url, sha256=report["source_file_sha256"],
            kind=product.kind, units=product.units, value=float(values[0, 0]) if valid else None,
            status="VALID_VALUE" if valid else "INVALID_NODATA"))
    status = "QUALITY_NOT_ASSESSED" if not results else (
        "QUALITY_LAYERS_PRESENT" if all(r.status == "VALID_VALUE" for r in results) else "PARTIAL_QUALITY_DATA")
    return QualityAssessment(status=status, layers=results)
