"""Backend-local DEM evidence; not a change to the shared analysis API."""
from typing import Annotated, Literal, Self

from pydantic import ConfigDict, Field, model_validator

from app.models.analysis import Azimuth, Coordinates, Elevation, Model, Nonnegative

SHA256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
FrameStatus = Literal["PRODUCT_SPECIFIC_VERIFIED", "SUPPORTED_BY_SOURCE_STANDARD", "PROVISIONAL", "UNKNOWN", "INCOMPATIBLE"]


class DemReference(Model):
    model_config = ConfigDict(frozen=True)
    product_id: str
    product_version: str | None
    version_evidence: str | None = None
    family: Literal["LROC_STEREO_DTM", "LOLA", "SYNTHETIC_TEST_FIXTURE"]
    provider_organization: str | None = None
    source_product_family: str | None = None
    source_url: str
    raster_sha256: SHA256
    label_sha256: SHA256 | None = None
    declared_lunar_radius_m: Literal[1737400]
    vertical_unit: Literal["m"]
    vertical_reference: Literal["HEIGHT_ABOVE_REFERENCE_SPHERE"]
    vertical_evidence: str
    declared_source_frame: str | None = None
    source_frame_evidence: Literal["SUPPORTED_BY_LROC_STANDARD", "PRODUCT_SPECIFIC_DOCUMENTED", "TEST_FIXTURE",
                                   "DECLARED_BY_MANIFEST", "PROVISIONAL", "UNKNOWN", "INCOMPATIBLE"]
    frame_evidence_source: str
    product_specific_frame_verified: bool = False
    target_spice_frame: Literal["MOON_ME_DE421"] = "MOON_ME_DE421"
    registration_uncertainty_status: Literal["NOT_QUANTIFIED"] = "NOT_QUANTIFIED"
    absolute_horizontal_error_m: Nonnegative | None = None
    absolute_vertical_error_m: Nonnegative | None = None
    relative_vertical_error_m: Nonnegative | None = None
    accuracy_source: str | None = None
    missing_constants: tuple[float, ...] = ()
    quality_layer_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = (
        "Pixel spacing is not measurement accuracy; no landing suitability is assessed.",
        "Locally calculated hashes identify files, not independent NASA authenticity.",
    )

    @property
    def frame_status(self) -> str:
        if self.product_specific_frame_verified:
            return "PRODUCT_SPECIFIC_VERIFIED"
        if self.source_frame_evidence == "SUPPORTED_BY_LROC_STANDARD":
            return "SUPPORTED_BY_SOURCE_STANDARD"
        if self.source_frame_evidence in ("UNKNOWN", "INCOMPATIBLE"):
            return self.source_frame_evidence
        return "PROVISIONAL"

    @model_validator(mode="after")
    def evidence_consistency(self) -> Self:
        if self.family == "LROC_STEREO_DTM" and self.label_sha256 is None:
            raise ValueError("LROC metre/datum evidence requires a pinned PDS label")
        if self.product_specific_frame_verified and self.source_frame_evidence != "PRODUCT_SPECIFIC_DOCUMENTED":
            raise ValueError("General mapping standards do not verify this product's frame")
        if self.family != "SYNTHETIC_TEST_FIXTURE" and self.source_frame_evidence == "TEST_FIXTURE":
            raise ValueError("Test fixture evidence cannot describe a real product")
        if self.declared_source_frame not in (None, self.target_spice_frame) and self.source_frame_evidence != "INCOMPATIBLE":
            raise ValueError("A different declared frame requires explicit incompatible evidence; no implicit rotation")
        if self.product_specific_frame_verified and self.declared_source_frame != self.target_spice_frame:
            raise ValueError("Product verification must identify the actual target frame")
        errors = (self.absolute_horizontal_error_m, self.absolute_vertical_error_m, self.relative_vertical_error_m)
        if any(value is not None for value in errors) and not self.accuracy_source:
            raise ValueError("Numerical errors require product-specific accuracy evidence")
        if self.product_version is None and not (self.family == "LOLA" and self.version_evidence):
            raise ValueError("Unknown version requires explicit LOLA evidence; hash identifies the inspected file")
        if self.product_version == "":
            raise ValueError("Empty product version")
        if not all((self.product_id, self.source_url,
                    self.vertical_evidence, self.frame_evidence_source)):
            raise ValueError("Product/version and evidence references must not be empty")
        return self


class QualitySample(Model):
    product_id: str
    product_version: str | None
    organization: str
    family: str
    source_url: str
    sha256: SHA256
    kind: Literal["COUNT", "HEIGHT_ERROR", "SLOPE", "EFFECTIVE_RESOLUTION"]
    units: str
    value: float | None
    status: Literal["VALID_VALUE", "INVALID_NODATA", "OUT_OF_RASTER_BOUNDS"]
    source_frame_evidence: Literal["MANIFEST_DECLARATION_NOT_PRODUCT_VERIFIED"] = "MANIFEST_DECLARATION_NOT_PRODUCT_VERIFIED"


class QualityAssessment(Model):
    status: Literal["QUALITY_NOT_ASSESSED", "QUALITY_LAYERS_PRESENT", "PARTIAL_QUALITY_DATA"] = "QUALITY_NOT_ASSESSED"
    layers: list[QualitySample] = Field(default_factory=list)
    interpretation: str = "Layer measurements only; no confidence score, landing hazard or operation suitability inferred."


class DemSample(Model):
    location: Coordinates
    product_id: str
    raster_sha256: SHA256
    status: Literal["VALID", "NODATA", "OUTSIDE_RASTER"]
    x_m: float
    y_m: float
    row_zero_based: int
    column_zero_based: int
    raw_value: float | None
    surface_elevation_m: float | None
    sampling_method: Literal["CONTAINING_CELL_NO_INTERPOLATION"] = "CONTAINING_CELL_NO_INTERPOLATION"
    reference: DemReference
    frame_status: FrameStatus
    resolution_m: tuple[float, float] | None = None
    crs_wkt: str | None = None
    auxiliary_file_hashes: dict[str, SHA256] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)
    quality: QualityAssessment = Field(default_factory=QualityAssessment)
    limitations: list[str] = Field(default_factory=list)
    prototype_registration_assumption_used: bool
    science_ready: Literal[False] = False

    @model_validator(mode="after")
    def no_missing_height(self) -> Self:
        if (self.status == "VALID") != (self.surface_elevation_m is not None):
            raise ValueError("Only a VALID cell has a surface elevation")
        if self.frame_status != self.reference.frame_status:
            raise ValueError("Sample frame status must match source evidence")
        if self.status == "VALID" and self.frame_status == "INCOMPATIBLE":
            raise ValueError("An incompatible source cannot provide a target-frame elevation")
        if self.prototype_registration_assumption_used == self.reference.product_specific_frame_verified:
            raise ValueError("Registration assumption must remain explicit for unverified sources")
        return self


class DiskCoverage(Model):
    location: Coordinates
    product_id: str
    radius_m: Annotated[float, Field(gt=0, le=5000)]
    disk_pixel_centres: Annotated[int, Field(gt=0)]
    inside_raster: Annotated[int, Field(ge=0)]
    valid_height_pixels: Annotated[int, Field(ge=0)]
    status: Literal["COMPLETE_SAMPLED_DISK", "BOUNDS_COMPLETE_DATA_PARTIAL",
                    "PARTIAL_RASTER_COVERAGE", "COVERAGE_INSUFFICIENT_FOR_FULL_5KM", "NO_VALID_HEIGHT_DATA"]
    prototype_registration_assumption_used: bool
    reference: DemReference
    frame_status: FrameStatus
    resolution_m: tuple[float, float] | None = None
    crs_wkt: str | None = None
    auxiliary_file_hashes: dict[str, SHA256] = Field(default_factory=dict)
    quality_status: Literal["QUALITY_NOT_ASSESSED"] = "QUALITY_NOT_ASSESSED"
    limitations: list[str] = Field(default_factory=list)
    method: Literal["PIXEL_CENTRE_GEODESIC_DISK_APPROXIMATE_AREA"] = "PIXEL_CENTRE_GEODESIC_DISK_APPROXIMATE_AREA"
    science_ready: Literal[False] = False

    @model_validator(mode="after")
    def ordered_counts(self) -> Self:
        if not 0 <= self.valid_height_pixels <= self.inside_raster <= self.disk_pixel_centres:
            raise ValueError("Coverage counts must include outside and missing samples")
        if self.frame_status != self.reference.frame_status:
            raise ValueError("Coverage frame status must match source evidence")
        return self

    def fractions(self) -> dict[str, float | None]:
        total = self.disk_pixel_centres
        return {
            "raster_bounds_fraction": self.inside_raster / total,
            "valid_height_fraction": self.valid_height_pixels / total,
            "unknown_or_missing_fraction": (total - self.valid_height_pixels) / total,
            "internal_nodata_fraction": (self.inside_raster - self.valid_height_pixels) / total,
            "outside_raster_fraction": (total - self.inside_raster) / total,
            "valid_height_fraction_inside_raster": self.valid_height_pixels / self.inside_raster if self.inside_raster else None,
        }


class RayCoverageEvidence(Model):
    """Future ray result envelope only. No ray tracing or visibility computation."""
    azimuth_deg: Azimuth
    requested_range_m: Annotated[float, Field(gt=0)]
    coverage_status: Literal["UNKNOWN", "INCOMPLETE"] = "UNKNOWN"
    partial_max_obstruction_elevation_deg: Elevation | None = None
    # This is never a complete horizon, even when a partial maximum is known.
    unobstructed_visibility_confirmed: Literal[False] = False

    @model_validator(mode="after")
    def unknown_is_not_computed(self) -> Self:
        if self.coverage_status == "UNKNOWN" and self.partial_max_obstruction_elevation_deg is not None:
            raise ValueError("A computed partial maximum needs INCOMPLETE coverage")
        return self
