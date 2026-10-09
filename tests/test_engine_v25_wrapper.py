import json
from pathlib import Path

import pandas as pd

from enterprise_finance.engine import BuildResult
from enterprise_finance import engine_v25


def test_v25_wrapper_publishes_lazy_project_asset_register(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for path in ["data/runtime", "data/processed", "web/data"]:
        Path(path).mkdir(parents=True)
    journal = pd.DataFrame([{
        "month": "2026-09", "entity": "DE01", "division": "Corporate", "account": "4000_EXTERNAL_REVENUE",
        "journal_id": "REV-1", "journal_type": "sale", "debit": 0.0, "credit": 100.0,
    }])
    journal.to_csv("data/runtime/journal.csv.gz", index=False, compression="gzip")
    pd.DataFrame(columns=["month", "project", "project_name", "entity", "division", "event", "amount", "go_live", "useful_life_months"]).to_csv("data/processed/capex.csv", index=False)
    Path("config").mkdir()
    Path("config/company.yml").write_text("capex_projects: []\n", encoding="utf-8")
    Path("data/processed/validation.json").write_text(json.dumps({"passed": True}), encoding="utf-8")
    Path("web/data/dashboard.json").write_text(json.dumps({"meta": {"version": "0.24.0"}, "validation": {"passed": True}}), encoding="utf-8")
    Path("web/data/manifest.json").write_text(json.dumps({"version": "0.24.0", "validation": {"passed": True}}), encoding="utf-8")

    monkeypatch.setattr(engine_v25, "build_v24", lambda *args, **kwargs: BuildResult("2026-09", 36, 24, 1, 1, 1, True))
    result = engine_v25.build("2026-09", allow_live_macro=False)

    manifest = json.loads(Path("web/data/manifest.json").read_text(encoding="utf-8"))
    dashboard = json.loads(Path("web/data/dashboard.json").read_text(encoding="utf-8"))
    detail = json.loads(Path("web/data/fixed_asset_detail.json").read_text(encoding="utf-8"))
    assert result.validation_passed
    assert manifest["version"] == dashboard["meta"]["version"] == "0.25.0"
    assert manifest["fixed_asset_project_rows"] == dashboard["meta"]["fixed_asset_project_count"] == detail["project_count"] == 0
    assert manifest["fixed_asset_detail_bytes"] > 0
    assert manifest["validation"]["fixed_asset_gross_ppe_max_gap"] == 0.0
    assert manifest["validation"]["passed"]
    assert Path("data/processed/fixed_asset_project_register.csv").exists()
    assert Path("data/processed/fixed_asset_project_events.csv").exists()
