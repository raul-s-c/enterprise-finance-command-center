from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

import numpy as np
import pandas as pd
import yaml


@dataclass(frozen=True)
class BuildResult:
    end_month: str
    journal_rows: int
    actual_months: int
    forecast_months: int
    validation_passed: bool


def load_config(path: str | Path = "config/company.yml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def month_range(end_month: str, periods: int) -> pd.PeriodIndex:
    end = pd.Period(end_month, freq="M")
    return pd.period_range(end=end, periods=periods, freq="M")


def macro_series(months: pd.PeriodIndex, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = np.arange(len(months))
    inflation = 0.022 + 0.004 * np.sin(t / 5) + rng.normal(0, 0.0015, len(t))
    industrial = 100 * np.cumprod(1 + 0.002 + rng.normal(0, 0.006, len(t)))
    energy = 100 * np.cumprod(1 + rng.normal(0.001, 0.025, len(t)))
    usd_eur = 0.91 + 0.025 * np.sin(t / 7) + rng.normal(0, 0.008, len(t))
    return pd.DataFrame({
        "month": months.astype(str),
        "inflation": inflation,
        "industrial_index": industrial,
        "energy_index": energy,
        "usd_eur": usd_eur,
    })


def operational_model(config: dict, months: pd.PeriodIndex, macro: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(config["group"]["seed"] + 11)
    rows = []
    entity_map = {
        "Software": ["DE01", "US01", "JP01"],
        "Hardware": ["DE01", "ES01", "US01", "JP01"],
        "Events": ["ES01", "US01"],
        "Spare Parts": ["ES01", "JP01"],
    }
    base = {"Software": 5_600_000, "Hardware": 9_200_000, "Events": 2_300_000, "Spare Parts": 3_100_000}
    season = {1: .88, 2: .92, 3: 1.00, 4: 1.01, 5: 1.03, 6: 1.05, 7: .94, 8: .83, 9: 1.04, 10: 1.08, 11: 1.12, 12: 1.18}
    for i, p in enumerate(months):
        m = macro.iloc[i]
        for div, entities in entity_map.items():
            for entity in entities:
                sensitivity = 1.0 if div == "Software" else float(m.industrial_index) / 100
                trend = (1.006 if div == "Software" else 1.003) ** i
                revenue = base[div] / len(entities) * season[p.month] * sensitivity * trend * rng.normal(1, 0.035)
                gm_lo, gm_hi = config["divisions"][div]["gross_margin_range"]
                gm = np.clip((gm_lo + gm_hi) / 2 - (float(m.energy_index) / 100 - 1) * (0.06 if div == "Hardware" else 0.015) + rng.normal(0, .012), gm_lo, gm_hi)
                mc_lo, mc_hi = config["divisions"][div]["marginal_contribution_range"]
                mc = np.clip((mc_lo + mc_hi) / 2 + rng.normal(0, .01), mc_lo, mc_hi)
                rows.append({"month": str(p), "entity": entity, "division": div, "revenue": round(revenue, 2), "gross_margin_pct": gm, "marginal_contribution_pct": mc})
    return pd.DataFrame(rows)


def add_line(lines: list[dict], month: str, entity: str, division: str, journal_id: str, account: str, debit: float = 0, credit: float = 0, counterparty: str = "EXTERNAL", description: str = "") -> None:
    lines.append({"month": month, "entity": entity, "division": division, "journal_id": journal_id, "account": account, "debit": round(debit, 2), "credit": round(credit, 2), "counterparty": counterparty, "description": description})


def build_journal(config: dict, operational: pd.DataFrame) -> pd.DataFrame:
    lines: list[dict] = []
    for n, r in operational.reset_index(drop=True).iterrows():
        rev = float(r.revenue)
        cogs = rev * (1 - float(r.gross_margin_pct))
        variable = rev * (1 - float(r.marginal_contribution_pct))
        fixed_prod = max(cogs - variable, 0)
        ar = rev
        jid = f"REV-{n:06d}"
        add_line(lines, r.month, r.entity, r.division, jid, "1100_AR", debit=ar, description="External sale")
        add_line(lines, r.month, r.entity, r.division, jid, "4000_REVENUE", credit=rev, description="External sale")
        jid = f"COGS-{n:06d}"
        add_line(lines, r.month, r.entity, r.division, jid, "5000_VARIABLE_COGS", debit=variable, description="Variable cost of sales")
        add_line(lines, r.month, r.entity, r.division, jid, "2100_AP", credit=variable, description="Variable cost of sales")
        if fixed_prod:
            add_line(lines, r.month, r.entity, r.division, jid, "5100_FIXED_PRODUCTION", debit=fixed_prod, description="Fixed production cost")
            add_line(lines, r.month, r.entity, r.division, jid, "2100_AP", credit=fixed_prod, description="Fixed production cost")
        opex = rev * ({"Software": .23, "Hardware": .11, "Events": .17, "Spare Parts": .12}[r.division])
        jid = f"OPEX-{n:06d}"
        add_line(lines, r.month, r.entity, r.division, jid, "6000_OPEX", debit=opex, description="Operating expenses")
        add_line(lines, r.month, r.entity, r.division, jid, "2100_AP", credit=opex, description="Operating expenses")
        capex = rev * (0.035 if r.division == "Hardware" else 0.01)
        jid = f"CAPEX-{n:06d}"
        add_line(lines, r.month, r.entity, r.division, jid, "1500_PPE", debit=capex, description="Capital expenditure")
        add_line(lines, r.month, r.entity, r.division, jid, "1000_CASH", credit=capex, description="Capital expenditure")
        dep = capex / 84
        jid = f"DEP-{n:06d}"
        add_line(lines, r.month, r.entity, r.division, jid, "6100_DEPRECIATION", debit=dep, description="Depreciation")
        add_line(lines, r.month, r.entity, r.division, jid, "1590_ACCUM_DEP", credit=dep, description="Depreciation")
        cash_collect = rev * 0.82
        jid = f"COLL-{n:06d}"
        add_line(lines, r.month, r.entity, r.division, jid, "1000_CASH", debit=cash_collect, description="Customer collections")
        add_line(lines, r.month, r.entity, r.division, jid, "1100_AR", credit=cash_collect, description="Customer collections")
        supplier_pay = (variable + fixed_prod + opex) * 0.78
        jid = f"PAY-{n:06d}"
        add_line(lines, r.month, r.entity, r.division, jid, "2100_AP", debit=supplier_pay, description="Supplier payments")
        add_line(lines, r.month, r.entity, r.division, jid, "1000_CASH", credit=supplier_pay, description="Supplier payments")
    return pd.DataFrame(lines)


def validate(journal: pd.DataFrame) -> dict:
    by_journal = journal.groupby("journal_id")[["debit", "credit"]].sum()
    journal_gap = float((by_journal.debit - by_journal.credit).abs().max())
    trial_gap = float(journal.debit.sum() - journal.credit.sum())
    result = {
        "journal_balance_max_gap": round(journal_gap, 2),
        "trial_balance_gap": round(trial_gap, 2),
        "passed": abs(journal_gap) < .01 and abs(trial_gap) < .01,
    }
    return result


def statements(journal: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    signed = journal.assign(amount=journal.debit - journal.credit)
    pnl_accounts = ["4000_REVENUE", "5000_VARIABLE_COGS", "5100_FIXED_PRODUCTION", "6000_OPEX", "6100_DEPRECIATION"]
    pnl = signed[signed.account.isin(pnl_accounts)].pivot_table(index=["month", "entity", "division"], columns="account", values="amount", aggfunc="sum", fill_value=0).reset_index()
    for c in pnl_accounts:
        if c not in pnl: pnl[c] = 0.0
    pnl["revenue"] = -pnl["4000_REVENUE"]
    pnl["marginal_contribution"] = pnl.revenue - pnl["5000_VARIABLE_COGS"]
    pnl["gross_profit"] = pnl.revenue - pnl["5000_VARIABLE_COGS"] - pnl["5100_FIXED_PRODUCTION"]
    pnl["ebit"] = pnl.gross_profit - pnl["6000_OPEX"] - pnl["6100_DEPRECIATION"]
    bs = signed.pivot_table(index=["month", "entity"], columns="account", values="amount", aggfunc="sum", fill_value=0).groupby(level=1).cumsum().reset_index()
    cf = signed[signed.account.eq("1000_CASH")].groupby(["month", "entity"], as_index=False).amount.sum().rename(columns={"amount":"net_cash_movement"})
    return pnl, bs, cf


def forecast(config: dict, operational: pd.DataFrame, end_month: str) -> pd.DataFrame:
    horizon = config["group"]["forecast_months"]
    future = pd.period_range(start=pd.Period(end_month, freq="M") + 1, periods=horizon, freq="M")
    last12 = operational[operational.month.isin(month_range(end_month, 12).astype(str))]
    base = last12.groupby(["entity", "division"], as_index=False).revenue.mean()
    rows = []
    for h, p in enumerate(future, start=1):
        for _, r in base.iterrows():
            growth = (1.006 if r.division == "Software" else 1.003) ** h
            rows.append({"vintage": end_month, "month": str(p), "entity": r.entity, "division": r.division, "revenue_forecast": round(float(r.revenue) * growth, 2), "horizon_month": h})
    return pd.DataFrame(rows)


def build(end_month: str, config_path: str = "config/company.yml") -> BuildResult:
    config = load_config(config_path)
    months = month_range(end_month, config["group"]["actual_months"])
    macro = macro_series(months, config["group"]["seed"])
    operational = operational_model(config, months, macro)
    journal = build_journal(config, operational)
    checks = validate(journal)
    if not checks["passed"]:
        raise RuntimeError(f"Financial controls failed: {checks}")
    pnl, bs, cf = statements(journal)
    fc = forecast(config, operational, end_month)
    out = Path("data/processed")
    out.mkdir(parents=True, exist_ok=True)
    macro.to_csv(out / "macro.csv", index=False)
    operational.to_csv(out / "operational.csv", index=False)
    journal.to_csv(out / "journal.csv", index=False)
    pnl.to_csv(out / "pnl.csv", index=False)
    bs.to_csv(out / "balance_sheet.csv", index=False)
    cf.to_csv(out / "cash_flow.csv", index=False)
    fc.to_csv(out / "forecast.csv", index=False)
    with open(out / "validation.json", "w", encoding="utf-8") as f: json.dump(checks, f, indent=2)
    web = Path("web/data")
    web.mkdir(parents=True, exist_ok=True)
    summary = pnl.groupby("month", as_index=False)[["revenue", "marginal_contribution", "gross_profit", "ebit"]].sum()
    summary.to_json(web / "summary.json", orient="records")
    fc.groupby("month", as_index=False).revenue_forecast.sum().to_json(web / "forecast.json", orient="records")
    manifest = {"end_month": end_month, "actual_months": len(months), "forecast_months": config["group"]["forecast_months"], "journal_rows": len(journal), "validation": checks}
    with open(web / "manifest.json", "w", encoding="utf-8") as f: json.dump(manifest, f, indent=2)
    return BuildResult(end_month, len(journal), len(months), config["group"]["forecast_months"], checks["passed"])
