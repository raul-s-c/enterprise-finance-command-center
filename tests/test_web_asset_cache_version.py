"""Keep GitHub Pages asset URLs aligned with the current release version."""
from pathlib import Path
import re
import tomllib
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def test_local_html_assets_use_current_release_cache_key():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    references = re.findall(r"(?:href|src)=\"([^\"]+)\"", html)
    local_references = [
        reference
        for reference in references
        if not reference.startswith(("https://", "http://", "data:", "#"))
    ]

    assert local_references
    for reference in local_references:
        parsed = urlsplit(reference)
        assert parsed.query == f"v={VERSION}", f"Stale cache key on {reference}"
        assert (WEB / parsed.path).is_file(), f"Missing local asset {parsed.path}"


def test_dashboard_data_fetch_uses_current_release_cache_key():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    match = re.search(r"fetch\(['\"]data/dashboard\.json\?v=([^'\"]+)", app)

    assert match, "The dashboard fetch must carry an explicit cache-busting key."
    assert match.group(1) == VERSION


def test_lazy_invoice_evidence_uses_the_published_dataset_version():
    explorer = (WEB / "contribution-explorer.js").read_text(encoding="utf-8")
    assert "data/ar_invoice_detail.json?v=${encodeURIComponent(data.meta.version)}" in explorer


def test_lazy_payable_item_evidence_uses_the_published_dataset_version():
    explorer = (WEB / "contribution-explorer.js").read_text(encoding="utf-8")
    assert "data/ap_item_detail.json?v=${encodeURIComponent(data.meta.version)}" in explorer


def test_lazy_fixed_asset_register_uses_the_published_dataset_version():
    statement = (WEB / "statement-workspace.js").read_text(encoding="utf-8")
    assert "data/fixed_asset_detail.json?v=${encodeURIComponent(button.dataset.version||'')}" in statement


def test_engine_version_matches_current_release():
    engine = (ROOT / "src" / "enterprise_finance" / "engine_v27.py").read_text(encoding="utf-8")
    match = re.search(r'^VERSION\s*=\s*"([^"]+)"$', engine, re.MULTILINE)

    assert match, "The active engine must declare its release version."
    assert match.group(1) == VERSION
