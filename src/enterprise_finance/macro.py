from __future__ import annotations

import csv
import io
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd


ECB_BASE = "https://data-api.ecb.europa.eu/service/data/EXR"
ECB_FM_BASE = "https://data-api.ecb.europa.eu/service/data/FM"
EUROSTAT_BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
WORLD_BANK_COMMODITIES = (
    "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/"
    "related/CMO-Historical-Data-Monthly.xlsx"
)

DRIVER_METADATA = {
    "inflation": ("Annual rate", "Eurostat HICP", "https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_minr/default/table"),
    "industrial_index": ("2021=100", "Eurostat industrial production", "https://ec.europa.eu/eurostat/databrowser/view/sts_inpr_m/default/table"),
    "energy_index": ("2010=100", "World Bank Pink Sheet energy index", WORLD_BANK_COMMODITIES),
    "policy_rate": ("Annual rate", "ECB main refinancing operations", "https://data.ecb.europa.eu/data/datasets/FM"),
    "USD": ("EUR per currency unit", "ECB reference exchange rate", "https://data.ecb.europa.eu/data/datasets/EXR"),
    "JPY": ("EUR per currency unit", "ECB reference exchange rate", "https://data.ecb.europa.eu/data/datasets/EXR"),
    "CNY": ("EUR per currency unit", "ECB reference exchange rate", "https://data.ecb.europa.eu/data/datasets/EXR"),
    "CZK": ("EUR per currency unit", "ECB reference exchange rate", "https://data.ecb.europa.eu/data/datasets/EXR"),
}


def _synthetic_macro(months: pd.PeriodIndex, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = np.arange(len(months), dtype=float)
    inflation = np.clip(0.024 - 0.00013 * t + 0.004 * np.sin(t / 5.0) + rng.normal(0, 0.0012, len(t)), 0.008, 0.055)
    industrial = 100.0 * np.cumprod(1 + 0.0018 + 0.004 * np.sin(t / 8.0) + rng.normal(0, 0.005, len(t)))
    energy = 100.0 * np.cumprod(1 + 0.001 + rng.normal(0, 0.022, len(t)))
    rates = np.clip(0.031 - 0.00028 * t + 0.003 * np.sin(t / 7.0), 0.008, 0.05)
    usd_per_eur = 1.08 + 0.045 * np.sin(t / 7.0) + rng.normal(0, 0.012, len(t))
    jpy_per_eur = 158 + 8 * np.sin(t / 9.0) + rng.normal(0, 2.0, len(t))
    cny_per_eur = 7.75 + 0.25 * np.sin(t / 10.0) + rng.normal(0, 0.08, len(t))
    czk_per_eur = 24.8 + 0.45 * np.sin(t / 11.0) + rng.normal(0, 0.10, len(t))
    return pd.DataFrame({
        "month": months.astype(str),
        "inflation": inflation,
        "industrial_index": industrial,
        "energy_index": energy,
        "policy_rate": rates,
        "EUR": 1.0,
        "USD": 1.0 / usd_per_eur,
        "JPY": 1.0 / jpy_per_eur,
        "CNY": 1.0 / cny_per_eur,
        "CZK": 1.0 / czk_per_eur,
        "macro_source": "deterministic_fallback",
        "inflation_source": "deterministic_fallback",
        "industrial_index_source": "deterministic_fallback",
        "energy_index_source": "deterministic_fallback",
        "policy_rate_source": "deterministic_fallback",
        "USD_source": "deterministic_fallback",
        "JPY_source": "deterministic_fallback",
        "CNY_source": "deterministic_fallback",
        "CZK_source": "deterministic_fallback",
    })


def _fetch_json(url: str, timeout: float = 5.0) -> dict:
    req = Request(url, headers={"User-Agent": "enterprise-finance-command-center/0.19"})
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _jsonstat_series(payload: dict) -> dict[str, float]:
    time_index = payload.get("dimension", {}).get("time", {}).get("category", {}).get("index", {})
    values = payload.get("value", {})
    if isinstance(time_index, list):
        positions = {str(value): idx for idx, value in enumerate(time_index)}
    else:
        positions = {str(key): int(value) for key, value in time_index.items()}
    out: dict[str, float] = {}
    for period, idx in positions.items():
        value = values.get(str(idx)) if isinstance(values, dict) else (values[idx] if idx < len(values) else None)
        if value is not None:
            out[period[:7]] = float(value)
    return out


def _fetch_eurostat_hicp(start: str, end: str) -> dict[str, float]:
    common = {"geo": "EA20", "unit": "RCH_A", "sinceTimePeriod": start, "untilTimePeriod": end}
    urls = [
        f"{EUROSTAT_BASE}/prc_hicp_manr?{urlencode({**common, 'coicop': 'CP00'})}",
        f"{EUROSTAT_BASE}/prc_hicp_minr?{urlencode({**common, 'coicop18': 'TOTAL'})}",
    ]
    out: dict[str, float] = {}
    for url in urls:
        try:
            values = _jsonstat_series(_fetch_json(url))
        except Exception:
            values = {}
        out.update({month: value / 100.0 for month, value in values.items()})
    return out


def _fetch_eurostat_industrial(start: str, end: str) -> dict[str, float]:
    query = urlencode({
        "geo": "EA20", "s_adj": "SCA", "nace_r2": "C", "indic_bt": "PRD", "unit": "I21",
        "sinceTimePeriod": start, "untilTimePeriod": end,
    })
    return _jsonstat_series(_fetch_json(f"{EUROSTAT_BASE}/sts_inpr_m?{query}"))


def _fetch_ecb_policy_rate(start: str, end: str, timeout: float = 5.0) -> dict[str, float]:
    end_date = pd.Period(end, freq="M").end_time.strftime("%Y-%m-%d")
    query = urlencode({"startPeriod": f"{start}-01", "endPeriod": end_date, "format": "csvdata"})
    req = Request(
        f"{ECB_FM_BASE}/D.U2.EUR.4F.KR.MRR_RT.LEV?{query}",
        headers={"User-Agent": "enterprise-finance-command-center/0.19"},
    )
    with urlopen(req, timeout=timeout) as response:
        text = response.read().decode("utf-8")
    out: dict[str, float] = {}
    for row in csv.DictReader(io.StringIO(text)):
        period, value = row.get("TIME_PERIOD"), row.get("OBS_VALUE")
        if period and value:
            out[period[:7]] = float(value) / 100.0
    return out


def _fetch_world_bank_energy(start: str, end: str, timeout: float = 10.0) -> dict[str, float]:
    req = Request(WORLD_BANK_COMMODITIES, headers={"User-Agent": "enterprise-finance-command-center/0.19"})
    with urlopen(req, timeout=timeout) as response:
        workbook = response.read()
    raw = pd.read_excel(io.BytesIO(workbook), sheet_name="Monthly Indices", header=None)
    out: dict[str, float] = {}
    for period, value in raw.iloc[9:, [0, 2]].itertuples(index=False, name=None):
        period = str(period)
        if len(period) != 7 or "M" not in period:
            continue
        month = f"{period[:4]}-{period[-2:]}"
        numeric = pd.to_numeric(value, errors="coerce")
        if pd.notna(numeric) and start <= month <= end:
            out[month] = float(numeric)
    return out


def _overlay(frame: pd.DataFrame, column: str, values: dict[str, float], source: str) -> int:
    if not values:
        return 0
    mask = frame["month"].isin(values)
    frame.loc[mask, column] = frame.loc[mask, "month"].map(values)
    frame.loc[mask, f"{column}_source"] = source
    return int(mask.sum())


def _fetch_ecb_monthly(currency: str, start: str, end: str, timeout: float = 3.0) -> dict[str, float]:
    if currency == "EUR":
        return {}
    key = f"M.{currency}.EUR.SP00.A"
    query = urlencode({"startPeriod": start, "endPeriod": end, "format": "csvdata"})
    req = Request(f"{ECB_BASE}/{key}?{query}", headers={"User-Agent": "enterprise-finance-command-center/0.2"})
    with urlopen(req, timeout=timeout) as response:
        text = response.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    out: dict[str, float] = {}
    for row in reader:
        period = row.get("TIME_PERIOD") or row.get("TIME PERIOD")
        value = row.get("OBS_VALUE") or row.get("OBS VALUE")
        if not period or not value:
            continue
        try:
            units_per_eur = float(value)
        except ValueError:
            continue
        if units_per_eur > 0:
            out[period[:7]] = 1.0 / units_per_eur
    return out


def build_macro(months: pd.PeriodIndex, seed: int, allow_live: bool = True) -> pd.DataFrame:
    frame = _synthetic_macro(months, seed)
    if not allow_live or len(months) == 0:
        return frame
    start, end = str(months[0]), str(months[-1])
    live_hits = 0
    for currency in ("USD", "JPY", "CNY", "CZK"):
        try:
            values = _fetch_ecb_monthly(currency, start, end)
        except Exception:
            values = {}
        live_hits += _overlay(frame, currency, values, "ECB_EXR")
    official_fetches = [
        ("inflation", _fetch_eurostat_hicp, "Eurostat_HICP"),
        ("industrial_index", _fetch_eurostat_industrial, "Eurostat_STS"),
        ("policy_rate", _fetch_ecb_policy_rate, "ECB_MRO"),
        ("energy_index", _fetch_world_bank_energy, "World_Bank_Pink_Sheet"),
    ]
    for column, fetcher, source in official_fetches:
        try:
            values = fetcher(start, end)
        except Exception:
            values = {}
        live_hits += _overlay(frame, column, values, source)
    if live_hits:
        source_columns = [f"{column}_source" for column in DRIVER_METADATA]
        official = frame[source_columns].ne("deterministic_fallback").any(axis=1)
        frame.loc[official, "macro_source"] = "official_public_sources_with_deterministic_fallback"
    return frame


def build_macro_lineage(macro: pd.DataFrame, close_month: str) -> pd.DataFrame:
    rows: list[dict] = []
    for row in macro.itertuples(index=False):
        record = row._asdict()
        for driver, (unit, official_source, source_url) in DRIVER_METADATA.items():
            source = str(record.get(f"{driver}_source", "deterministic_fallback"))
            rows.append({
                "close_month": close_month,
                "observation_month": str(record["month"]),
                "driver": driver,
                "value": round(float(record[driver]), 8),
                "unit": unit,
                "source": source,
                "official_source": official_source,
                "source_url": source_url,
                "status": "Official" if source != "deterministic_fallback" else "Fallback",
            })
    return pd.DataFrame(rows)


def source_manifest(macro: pd.DataFrame) -> dict:
    drivers = {}
    for driver, (unit, official_source, source_url) in DRIVER_METADATA.items():
        source_column = f"{driver}_source"
        source = macro[source_column] if source_column in macro else pd.Series("deterministic_fallback", index=macro.index)
        official_mask = source.ne("deterministic_fallback")
        official_months = macro.loc[official_mask, "month"].astype(str)
        drivers[driver] = {
            "unit": unit,
            "preferred_source": official_source,
            "source_url": source_url,
            "fallback": "deterministic calibrated series",
            "official_rows": int(official_mask.sum()),
            "fallback_rows": int((~official_mask).sum()),
            "latest_official_month": str(official_months.max()) if not official_months.empty else None,
        }
    return {
        "fx": {
            "preferred_source": "ECB Data Portal EXR monthly reference rates",
            "fallback": "deterministic synthetic FX curves",
            "live_rows": int(sum(drivers[currency]["official_rows"] for currency in ("USD", "JPY", "CNY", "CZK"))),
        },
        "economic_drivers": {
            "current": "official public observations by driver with deterministic month-level fallback",
            "planned": [],
        },
        "macro_drivers": drivers,
    }
