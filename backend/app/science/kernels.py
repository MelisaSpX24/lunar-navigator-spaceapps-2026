"""Exclusive, process-local kernel ownership. No downloads or implicit READY."""
from contextlib import contextmanager
from pathlib import Path
from threading import RLock

import spiceypy as spice
from spiceypy.utils.exceptions import SpiceyError
from spiceypy.utils.support_types import SPICEINT_CELL
from pydantic import Field

from app.models.analysis import Model
from app.data.manifest import sha256_file

LOCK = RLock()
FILES = {"de421.bsp": ("DAF", "SPK"),
         "moon_pa_de421_1900-2050.bpc": ("DAF", "PCK"),
         "moon_080317.tf": ("KPL", "FK"),
         "naif0012.tls": ("KPL", "LSK"), "pck00011.tpc": ("KPL", "PCK")}


class ScienceError(RuntimeError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(f"{code}: {message}")


class KernelFile(Model):
    filename: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class KernelIndex(Model):
    files: list[KernelFile]


def read_index(directory: Path, index_path: Path) -> list[dict]:
    index = KernelIndex.model_validate_json(index_path.read_text())
    if len(index.files) != len(FILES) or {v.filename for v in index.files} != set(FILES):
        raise ScienceError("KERNEL_PACKAGE_MISMATCH", "Require exactly the five approved DE421 candidates")
    records = []
    for item in index.files:
        path = directory / item.filename
        if not path.is_file():
            raise ScienceError("KERNEL_MISSING", item.filename)
        if sha256_file(path) != item.sha256:
            raise ScienceError("KERNEL_HASH_MISMATCH", item.filename)
        try:
            kind = spice.getfat(str(path))
        except SpiceyError as exc:
            raise ScienceError("KERNEL_INVALID", item.filename) from exc
        if kind != FILES[item.filename]:
            raise ScienceError("KERNEL_TYPE_MISMATCH", f"{item.filename}: {kind}")
        records.append({"filename": item.filename, "sha256": item.sha256,
                        "path": str(path.resolve()), "architecture": kind[0], "kind": kind[1]})
    return records


def intervals(cell):
    return [[float(a), float(b)] for a,b in (spice.wnfetd(cell,i) for i in range(spice.wncard(cell)))]


class KernelSession:
    def __init__(self, directory, index_path):
        self.directory, self.index_path = Path(directory), Path(index_path)
        self.active = False

    def __enter__(self):
        LOCK.acquire()
        owned = False
        try:
            if spice.ktotal("ALL"):
                raise ScienceError("KERNEL_POOL_IN_USE", "Use an isolated worker; existing pool is not cleared")
            self.records = read_index(self.directory, self.index_path)
            owned = True
            for record in self.records:
                spice.furnsh(record["path"])
            if spice.namfrm("MOON_ME_DE421") != 31007 or spice.namfrm("MOON_PA_DE421") != 31006:
                raise ScienceError("FRAME_MISMATCH", "Missing expected DE421 lunar frames")
            _, class_id, frame_id = spice.frinfo(31006)
            if (class_id, frame_id) != (2, 31006):
                raise ScienceError("FRAME_MISMATCH", "Unexpected lunar orientation frame")
            radii = spice.bodvrd("MOON", "RADII", 3)[1]
            if any(abs(float(r)-1737.4) > 1e-6 for r in radii):
                raise ScienceError("SHAPE_MISMATCH", "Expected 1737.4 km reference sphere")
            self.coverage = self._coverage()
            self.active = True
            return self
        except Exception as exc:
            if owned:
                spice.kclear()
            LOCK.release()
            if isinstance(exc, SpiceyError):
                raise ScienceError("KERNEL_LOAD_OR_COMPATIBILITY_ERROR", exc.short) from exc
            raise

    def __exit__(self, *args):
        try:
            spice.kclear()
            self.active = False
        finally:
            LOCK.release()

    def _coverage(self):
        spk = str(self.directory / "de421.bsp")
        pck = str(self.directory / "moon_pa_de421_1900-2050.bpc")
        objects = set(int(i) for i in spice.spkobj(spk))
        if not {10,301,399}.issubset(objects):
            raise ScienceError("SPK_OBJECTS_MISSING", "Sun, Moon or Earth not present")
        frame_cell = SPICEINT_CELL(100)
        spice.pckfrm(pck, frame_cell)
        frames = set(int(i) for i in frame_cell)
        if 31006 not in frames:
            raise ScienceError("PCK_FRAME_MISSING", "DE421 principal axes orientation absent")
        return {str(i): intervals(spice.spkcov(spk,i)) for i in (10,301,399)} | {
            "orientation": intervals(spice.pckcov(pck,31006))}

    @contextmanager
    def call(self):
        with LOCK:
            if not self.active:
                raise ScienceError("KERNEL_SESSION_INACTIVE", "Enter a kernel session first")
            try:
                yield
            except SpiceyError as exc:
                code = "KERNEL_COVERAGE_OR_DATA_ERROR" if "INSUFF" in exc.short or "NOTFOUND" in exc.short else "SPICE_ERROR"
                raise ScienceError(code, exc.short) from exc

    def check_epoch(self, et):
        for name, ranges in self.coverage.items():
            if not any(a <= et <= b for a,b in ranges):
                raise ScienceError("EPOCH_OUT_OF_COVERAGE", f"No {name} coverage at ET {et}")
        # Corrected light-time epochs and complete SPK chains are additionally
        # checked by the actual SPICE call; centre-epoch intervals are necessary, not sufficient.
