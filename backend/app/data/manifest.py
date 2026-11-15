"""Provenance declarations, explicitly distinct from inspected files."""
import hashlib
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator

from app.models.analysis import Model


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Product(Model):
    id: str
    organization: str
    family: str
    source_url: str
    download_url: str | None = None
    filename: str
    kind: Literal["ELEVATION", "SLOPE", "HEIGHT_ERROR", "SLOPE_ERROR", "EFFECTIVE_RESOLUTION", "COUNT", "ROI", "SPK", "PCK", "FK", "LSK"]
    resolution_m: float | None = None
    geographic_coverage: str | None = None
    frame: str | None = None
    projection: str | None = None
    units: str | None = None
    height_datum: str | None = None
    nodata: float | None = None
    quality_layer_ids: list[str] = Field(default_factory=list)
    size_bytes: int | None = None
    reported_size: str | None = None
    version: str | None = None
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    local_path: str | None = None
    status: Literal["PAGE_DOCUMENTED", "UNVERIFIED", "FILE_INSPECTED", "READY"] = "UNVERIFIED"
    time_coverage: str | None = None
    limitations: list[str]

    @model_validator(mode="after")
    def no_unearned_readiness(self) -> Self:
        if self.status in ("FILE_INSPECTED", "READY"):
            if self.local_path is None or not Path(self.local_path).is_file():
                raise ValueError("Inspected/READY requires an existing local file")
            if self.sha256 is None or sha256_file(Path(self.local_path)) != self.sha256:
                raise ValueError("Inspected/READY requires a matching file SHA-256")
        if self.status == "READY":
            raise ValueError("Command 02 does not establish scientific READY status")
        if self.local_path is None and self.sha256 is not None:
            raise ValueError("No file hash without a local file")
        return self


class Manifest(Model):
    schema_version: Literal["1.0"]
    science_ready: Literal[False]
    access_notes: list[str]
    products: list[Product]

    @model_validator(mode="after")
    def unique_products(self) -> Self:
        ids = [p.id for p in self.products]
        if len(ids) != len(set(ids)):
            raise ValueError("Product IDs must be unique")
        if any(q not in ids for p in self.products for q in p.quality_layer_ids):
            raise ValueError("Unknown quality-layer ID")
        return self
