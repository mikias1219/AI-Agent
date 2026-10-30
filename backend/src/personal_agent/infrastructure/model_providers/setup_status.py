"""Public progress of the approved background model setup, excluding private settings."""

import json
from pathlib import Path


class ModelSetupStatus:
    def __init__(self, path: Path = Path("data/fast-model-setup.json")) -> None:
        self._path = path

    def read(self) -> dict | None:
        try:
            data = json.loads(self._path.read_text())
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict) or not isinstance(data.get("status"), str):
            return None
        return {
            key: data[key]
            for key in ("status", "model", "updated_at", "restart_required")
            if key in data and isinstance(data[key], (str, bool))
        }
