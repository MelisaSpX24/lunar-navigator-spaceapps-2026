"""Explicit LOLA elevation declaration adapter; missing datum is never guessed."""
from pathlib import Path

from app.data.dem_models import DemReference
from app.data.coordinates import LunarGrid
from app.data.errors import DemError
from app.data.manifest import Product, sha256_file
from app.data.raster import open_local


def lola_reference(path, product: Product, *, vertical_evidence: str, version_evidence: str | None = None) -> DemReference:
    """Requires inspected/externally documented vertical evidence from the caller.

    This does not edit or promote the original manifest or verify registration.
    Page-only manifests lack the required datum evidence and fail. An absent
    publisher version can remain null only with explicit version evidence.
    """
    if product.family not in ("PGDA Product 78", "PGDA Product 90") or product.kind != "ELEVATION":
        raise DemError("WRONG_PRODUCT_FAMILY", "This adapter accepts declared PGDA LOLA elevation products only")
    if product.units != "m":
        raise DemError("UNKNOWN_VERTICAL_UNIT", "Explicit metre elevation evidence is required")
    if product.height_datum != "HEIGHT_ABOVE_REFERENCE_SPHERE" or not vertical_evidence.strip():
        raise DemError("UNKNOWN_VERTICAL_DATUM", "Reference-sphere height must be explicitly documented")
    if product.frame != "MOON_ME_DE421":
        raise DemError("INCOMPATIBLE_FRAME", "LOLA declaration must identify the intended DE421 frame")
    if (not product.version and not version_evidence) or Path(path).name != product.filename:
        raise DemError("SOURCE_METADATA_INCOMPLETE", "Product version or explicit missing-version evidence and matching filename are required")
    digest = sha256_file(Path(path))
    if product.sha256 is not None and digest != product.sha256:
        raise DemError("SOURCE_HASH_MISMATCH", "LOLA file differs from its manifest hash")
    with open_local(path) as ds:
        grid = LunarGrid(ds)
        radius_m = int(grid.crs.ellipsoid.semi_major_metre)
    return DemReference(
        product_id=product.id, product_version=product.version, family="LOLA",
        version_evidence=version_evidence,
        provider_organization=product.organization, source_product_family=product.family,
        source_url=product.source_url, raster_sha256=digest, vertical_evidence=vertical_evidence,
        declared_lunar_radius_m=radius_m, vertical_unit="m", vertical_reference="HEIGHT_ABOVE_REFERENCE_SPHERE",
        declared_source_frame=product.frame, source_frame_evidence="DECLARED_BY_MANIFEST",
        frame_evidence_source=product.source_url, product_specific_frame_verified=False,
        quality_layer_ids=product.quality_layer_ids, limitations=product.limitations)
