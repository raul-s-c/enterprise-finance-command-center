from __future__ import annotations

import json

import pandas as pd

from . import engine as base_engine
from . import engine_v10 as engine_v10_module
from .contract_settlement_v10 import apply_contract_liability_accounting as cent_precise_contract_settlement
from .forecasting import validate_forecast_scale


VERSION = "0.10.0"


def _read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    """Finalize the v0.10 close after the contract-aware rebuild.

    Contract settlement is injected at cent precision before running the v0.10
    rebuild. The wrapper then reasserts forecast-scale/no-lookahead controls from
    v0.9.1, validates customer refunds and publishes exact Entity/Division
    contract summaries.
    """
    engine_v10_module.apply_contract_liability_accounting = cent_precise_contract_settlement
    result = engine_v10_module.build(
        end_month, config_path=config_path, allow_live_macro=allow_live_macro
    )

    operations = _read_csv("data/runtime/operational.csv.gz")
    journal = _read_csv("data/runtime/journal.csv.gz")
    forecasts = _read_csv("data/processed/forecast_vintages.csv")
    products = _read_csv("data/processed/products.csv")
    contracts = _read_csv("data/processed/contract_liabilities.csv")
    advances = _read_csv("data/processed/customer_advances.csv")

    forecast_scale = validate_forecast_scale(forecasts, operations, end_month)
    lookahead_errors = int(
        (pd.PeriodIndex(forecasts.month, freq="M") <= pd.PeriodIndex(forecasts.vintage, freq="M")).sum()
    ) if not forecasts.empty else 0

    refunds = journal[journal.journal_type.eq("customer_advance_refund")].copy()
    refund_balance_gap = 0.0
    if not refunds.empty:
        by_refund = refunds.groupby("journal_id", as_index=False).agg(debit=("debit", "sum"), credit=("credit", "sum"))
        refund_balance_gap = float((by_refund.debit - by_refund.credit).abs().max())

    with open("data/processed/validation.json", "r", encoding="utf-8") as handle:
        checks = json.load(handle)
    checks.update({key: value for key, value in forecast_scale.items() if key != "passed"})
    checks["forecast_lookahead_errors"] = lookahead_errors
    checks["catalog_product_count"] = int(len(products))
    checks["catalog_family_count"] = int(products[["division", "product_family"]].drop_duplicates().shape[0])
    checks["sold_product_count"] = int(operations["product"].nunique())
    checks["contract_refund_journal_max_gap"] = round(refund_balance_gap, 2)
    checks["passed"] = bool(
        checks.get("passed", False)
        and forecast_scale["passed"]
        and lookahead_errors == 0
        and checks["catalog_product_count"] >= 200
        and checks["sold_product_count"] >= 150
        and refund_balance_gap <= 0.02
    )
    if not checks["passed"]:
        raise RuntimeError(f"v0.10 final release controls failed: {checks}")

    latest_contracts = contracts[contracts.month.eq(end_month)].copy() if not contracts.empty else pd.DataFrame()
    latest_advances = advances[advances.month.eq(end_month)].copy() if not advances.empty else pd.DataFrame()
    if latest_contracts.empty:
        entity_summary = pd.DataFrame(columns=["entity", "division", "contract_liabilities", "customer_advances"])
    else:
        entity_summary = latest_contracts.groupby(["entity", "division"], as_index=False).contract_liability.sum().rename(
            columns={"contract_liability": "contract_liabilities"}
        )
        if not latest_advances.empty:
            receipt_summary = latest_advances.groupby(["entity", "division"], as_index=False).advance_amount.sum().rename(
                columns={"advance_amount": "customer_advances"}
            )
            entity_summary = entity_summary.merge(receipt_summary, on=["entity", "division"], how="outer")
        entity_summary = entity_summary.fillna(0.0)

    refund_cash = refunds[refunds.account.eq("1000_CASH")].copy() if not refunds.empty else pd.DataFrame()
    latest_refund_cash = refund_cash[refund_cash.month.eq(end_month)] if not refund_cash.empty else pd.DataFrame()
    end = pd.Period(end_month, freq="M")
    trailing_start = str(end - 11)
    trailing_refund_cash = refund_cash[
        refund_cash.month.ge(trailing_start) & refund_cash.month.le(end_month)
    ] if not refund_cash.empty else pd.DataFrame()

    with open("data/processed/validation.json", "w", encoding="utf-8") as handle:
        json.dump(checks, handle, indent=2)

    with open("web/data/dashboard.json", "r", encoding="utf-8") as handle:
        dashboard = json.load(handle)
    dashboard["meta"]["version"] = VERSION
    dashboard["contract_entity_summary"] = base_engine._records(entity_summary)
    dashboard["contract_liability_detail"] = base_engine._records(
        latest_contracts.sort_values("contract_liability", ascending=False).head(500)
    ) if not latest_contracts.empty else []
    dashboard["customer_advances"] = base_engine._records(
        latest_advances.sort_values("advance_amount", ascending=False).head(500)
    ) if not latest_advances.empty else []
    dashboard["contract_refunds"] = base_engine._records(
        refund_cash.sort_values(["month", "credit"], ascending=[False, False]).head(500)
    ) if not refund_cash.empty else []
    dashboard["validation"] = checks
    with open("web/data/dashboard.json", "w", encoding="utf-8") as handle:
        json.dump(dashboard, handle, separators=(",", ":"), allow_nan=False)

    with open("web/data/manifest.json", "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    manifest["version"] = VERSION
    manifest["forecast_next_month_scale_ratio"] = round(float(forecast_scale["forecast_next_month_scale_ratio"]), 4)
    manifest["forecast_lookahead_errors"] = lookahead_errors
    manifest["contract_entity_division_rows"] = int(len(entity_summary))
    manifest["contract_refund_journal_rows"] = int(len(refunds))
    manifest["latest_customer_advance_refunds"] = round(float(latest_refund_cash.credit.sum()), 2) if not latest_refund_cash.empty else 0.0
    manifest["trailing_12m_customer_advance_refunds"] = round(float(trailing_refund_cash.credit.sum()), 2) if not trailing_refund_cash.empty else 0.0
    manifest["validation"] = checks
    with open("web/data/manifest.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    return result
