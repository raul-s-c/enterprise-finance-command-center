"""24-month integrated forecast release wrapper."""
from __future__ import annotations

import json
from pathlib import Path

from .engine_v21 import _dump_json, build as build_v21

VERSION = "0.22.1"


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    result = build_v21(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    for name in ("web/data/dashboard.json", "web/data/manifest.json"):
        path = Path(name)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if name.endswith("dashboard.json"):
            payload["meta"]["version"] = VERSION
        else:
            payload["version"] = VERSION
        _dump_json(payload, name, allow_nan=False, separators=(",", ":") if name.endswith("dashboard.json") else None, indent=None if name.endswith("dashboard.json") else 2)
    return result
