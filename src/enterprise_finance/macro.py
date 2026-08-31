from __future__ import annotations

import csv
import io
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd


ECB_BASE = "https://data-api.ecb.europa.eu/service/data/EXR"


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
    })


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
    live_months: set[str] = set()
    for currency in ("USD", "JPY", "CNY", "CZK"):
        try:
            values = _fetch_ecb_monthly(currency, start, end)
        except Exception:
            values = {}
        if values:
            mask = frame["month"].isin(values)
            frame.loc[mask, currency] = frame.loc[mask, "month"].map(values)
            live_hits += int(mask.sum())
            live_months.update(values.keys())
    if live_hits:
        frame["macro_source"] = np.where(
            frame["month"].isin(live_months),
            "ECB_FX_plus_deterministic_macro",
            frame["macro_source"],
        )
    return frame


def source_manifest(macro: pd.DataFrame) -> dict:
    return {
        "fx": {
            "preferred_source": "ECB Data Portal EXR monthly reference rates",
            "fallback": "deterministic synthetic FX curves",
            "live_rows": int(macro["macro_source"].str.contains("ECB", na=False).sum()),
        },
        "economic_drivers": {
            "current": "deterministic macro indices calibrated to plausible ranges",
            "planned": ["Eurostat industrial production", "Eurostat HICP", "World Bank commodity indices"],
        },
    }
