"""Stable backend-local DEM failures; no HTTP contract changes."""


class DemError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")
