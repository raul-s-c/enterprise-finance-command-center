from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from .accounting import cash_flow
from .contract_liabilities import chart_of_accounts_with_contracts, group_balance_sheet_with_contracts, legal_balance_sheet_with_contracts


TREASURY_RECEIVABLE = "1160_IC_TREASURY_RECEIVABLE"
TREASURY_PAYABLE = "2160_IC_TREASURY_PAYABLE"


def chart_of_accounts_with_treasury() -> pd.DataFrame:
    base = chart_of_accounts_with_contracts()
    extra = pd.DataFrame([
        {"account": TREASURY_RECEIVABLE, "statement": "Balance Sheet", "line": "Intercompany Treasury Receivable", "account_type": "Asset"},
        {"account": TREASURY_PAYABLE, "statement": "Balance Sheet", "line": "Intercompany Treasury Payable", "account_type": "Liability"},
    ])
    return pd.concat([base, extra], ignore_index=True).drop_duplicates("account", keep="last")


def _row(*, month: str, entity: str, journal_id: str, account: str, debit: float = 0.0, credit: float = 0.0, counterparty: str, description: str) -> dict:
    return {
        "month": month,
        "entity": entity,
        "division": "Corporate",
        "journal_id": journal_id,
        "journal_type": "treasury_cash_pool",
        "account": account,
        "debit": round(float(debit), 2),
        "credit": round(float(credit), 2),
        "counterparty": counterparty,
        "description": description,
        "cash_flow_category": "intercompany_treasury",
        "product": "",
        "customer": "",
    }


def _treasury_cfg(config: dict) -> dict:
    cfg = config.get("treasury", {})
    minimums = {str(k): float(v) for k, v in cfg.get("minimum_cash_by_entity", {}).items()}
    return {
        "hq_entity": str(cfg.get("hq_entity", "DE01")),
        "minimum_cash_default": float(cfg.get("minimum_cash_default", 3_000_000.0)),
        "minimum_cash_by_entity": minimums,
        "sweep_buffer": float(cfg.get("sweep_buffer", 1_000_000.0)),
        "sweep_ratio": float(cfg.get("sweep_ratio", 0.80)),
        "rcf_limit": float(cfg.get("rcf_limit", 35_000_000.0)),
        "net_leverage_limit": float(cfg.get("net_leverage_limit", 2.50)),
        "interest_coverage_min": float(cfg.get("interest_coverage_min", 4.00)),
        "debt_maturities": {str(k): str(v) for k, v in cfg.get("debt_maturities", {}).items()},
    }


def _minimum_cash(entity: str, cfg: dict) -> float:
    return float(cfg["minimum_cash_by_entity"].get(entity, cfg["minimum_cash_default"]))


def _base_cash_movements(journal: pd.DataFrame) -> pd.DataFrame:
    cash = journal[journal.account.eq("1000_CASH")].copy()
    cash["movement"] = cash.debit - cash.credit
    return cash.groupby(["month", "entity"], as_index=False).movement.sum()


def append_cash_pool_journals(journal: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply a deterministic zero-sum legal-entity cash pool.

    Non-HQ entities keep an operating minimum plus a liquidity buffer. A share of
    surplus cash is swept to HQ. If local cash falls below its minimum, HQ funds
    the entity back to minimum. Reciprocal treasury receivable/payable accounts
    preserve legal-entity Balance Sheet integrity while eliminating at group level.
    """
    if journal.empty:
        return journal.copy(), pd.DataFrame()
    cfg = _treasury_cfg(config)
    hq = cfg["hq_entity"]
    entities = sorted(str(x) for x in journal.entity.unique())
    if hq not in entities:
        raise ValueError(f"Treasury HQ entity {hq} is not present in the ledger")

    base_movements = _base_cash_movements(journal)
    months = sorted(str(x) for x in journal.month.unique())
    cash_balance: dict[str, float] = defaultdict(float)
    rows: list[dict] = []
    schedule: list[dict] = []

    for month in months:
        for r in base_movements[base_movements.month.eq(month)].itertuples(index=False):
            cash_balance[str(r.entity)] = round(cash_balance[str(r.entity)] + float(r.movement), 2)

        transfers: list[tuple[str, str, float, str]] = []
        for entity in entities:
            if entity == hq:
                continue
            minimum = _minimum_cash(entity, cfg)
            buffer = float(cfg["sweep_buffer"])
            local_cash = float(cash_balance[entity])
            if local_cash > minimum + buffer:
                sweep = round((local_cash - minimum - buffer) * float(cfg["sweep_ratio"]), 2)
                if sweep > 0.005:
                    transfers.append((entity, hq, sweep, "surplus_sweep"))
            elif local_cash < minimum:
                funding = round(minimum - local_cash, 2)
                if funding > 0.005:
                    transfers.append((hq, entity, funding, "liquidity_funding"))

        for source, destination, amount, transfer_type in transfers:
            jid = f"POOL-{month}-{source}-{destination}-{transfer_type}"
            # Source sends cash and receives an intercompany treasury asset.
            rows.append(_row(month=month, entity=source, journal_id=jid + "-S", account=TREASURY_RECEIVABLE, debit=amount, counterparty=destination, description=f"Treasury cash pool {transfer_type}"))
            rows.append(_row(month=month, entity=source, journal_id=jid + "-S", account="1000_CASH", credit=amount, counterparty=destination, description=f"Treasury cash pool {transfer_type}"))
            # Destination receives cash and recognizes the reciprocal treasury liability.
            rows.append(_row(month=month, entity=destination, journal_id=jid + "-D", account="1000_CASH", debit=amount, counterparty=source, description=f"Treasury cash pool {transfer_type}"))
            rows.append(_row(month=month, entity=destination, journal_id=jid + "-D", account=TREASURY_PAYABLE, credit=amount, counterparty=source, description=f"Treasury cash pool {transfer_type}"))
            cash_balance[source] = round(cash_balance[source] - amount, 2)
            cash_balance[destination] = round(cash_balance[destination] + amount, 2)
            schedule.append({
                "month": month,
                "source_entity": source,
                "destination_entity": destination,
                "transfer_type": transfer_type,
                "amount": amount,
            })

    pool_journal = pd.DataFrame(rows, columns=journal.columns)
    adjusted = pd.concat([journal, pool_journal], ignore_index=True) if not pool_journal.empty else journal.copy()
    return adjusted, pd.DataFrame(schedule)


def _treasury_balances(journal: pd.DataFrame) -> pd.DataFrame:
    scope = journal[journal.account.isin([TREASURY_RECEIVABLE, TREASURY_PAYABLE])].copy()
    months = sorted(str(x) for x in journal.month.unique())
    entities = sorted(str(x) for x in journal.entity.unique())
    if scope.empty:
        return pd.MultiIndex.from_product([months, entities], names=["month", "entity"]).to_frame(index=False).assign(
            treasury_receivable=0.0, treasury_payable=0.0
        )
    scope["signed"] = scope.debit - scope.credit
    monthly = scope.groupby(["month", "entity", "account"], as_index=False).signed.sum()
    running: dict[tuple[str, str], float] = defaultdict(float)
    rows: list[dict] = []
    for month in months:
        for r in monthly[monthly.month.eq(month)].itertuples(index=False):
            running[(str(r.entity), str(r.account))] += float(r.signed)
        for entity in entities:
            rows.append({
                "month": month,
                "entity": entity,
                "treasury_receivable": running[(entity, TREASURY_RECEIVABLE)],
                "treasury_payable": -running[(entity, TREASURY_PAYABLE)],
            })
    return pd.DataFrame(rows)


def legal_balance_sheet_with_treasury(journal: pd.DataFrame) -> pd.DataFrame:
    base = legal_balance_sheet_with_contracts(journal)
    treasury = _treasury_balances(journal)
    out = base.merge(treasury, on=["month", "entity"], how="left").fillna({"treasury_receivable": 0.0, "treasury_payable": 0.0})
    out["assets"] = out.assets + out.treasury_receivable
    out["liabilities"] = out.liabilities + out.treasury_payable
    out["balance_check"] = out.assets - out.liabilities - out.equity
    return out


def group_balance_sheet_with_treasury(legal_bs: pd.DataFrame, markup: float) -> pd.DataFrame:
    # The existing group balance sheet intentionally excludes treasury receivable
    # and payable columns. Because they are exactly reciprocal, that omission is
    # the consolidation elimination. Group cash remains the sum of legal cash.
    return group_balance_sheet_with_contracts(legal_bs, markup)


def cash_flow_with_treasury(journal: pd.DataFrame) -> pd.DataFrame:
    out = cash_flow(journal).copy()
    cash = journal[journal.account.eq("1000_CASH")].copy()
    cash["cash_movement"] = cash.debit - cash.credit
    treasury = cash[cash.cash_flow_category.eq("intercompany_treasury")].groupby(["month", "entity"], as_index=False).cash_movement.sum().rename(columns={"cash_movement": "intercompany_treasury"})
    out = out.merge(treasury, on=["month", "entity"], how="left").fillna({"intercompany_treasury": 0.0})
    out["financing_cash_flow"] = out.financing_cash_flow + out.intercompany_treasury
    out["net_cash_movement"] = out.net_cash_movement + out.intercompany_treasury
    return out


def debt_schedule(journal: pd.DataFrame, management: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cfg = _treasury_cfg(config)
    entities = sorted(str(x) for x in journal.entity.unique())
    months = sorted(str(x) for x in journal.month.unique())

    debt_j = journal[journal.account.eq("2500_DEBT")].copy()
    debt_j["movement"] = debt_j.credit - debt_j.debit
    debt_monthly = debt_j.groupby(["month", "entity"], as_index=False).movement.sum()
    interest_j = journal[(journal.account.eq("7000_INTEREST")) & ~journal.journal_type.eq("closing")].copy()
    interest_j["interest_expense"] = interest_j.debit - interest_j.credit
    interest_monthly = interest_j.groupby(["month", "entity"], as_index=False).interest_expense.sum()

    running: dict[str, float] = defaultdict(float)
    rows: list[dict] = []
    for month in months:
        for r in debt_monthly[debt_monthly.month.eq(month)].itertuples(index=False):
            running[str(r.entity)] += float(r.movement)
        interest_map = {str(r.entity): float(r.interest_expense) for r in interest_monthly[interest_monthly.month.eq(month)].itertuples(index=False)}
        for entity in entities:
            debt = max(running[entity], 0.0)
            interest = max(interest_map.get(entity, 0.0), 0.0)
            implied_rate = interest * 12.0 / debt if debt > 0.005 else 0.0
            rows.append({
                "month": month,
                "entity": entity,
                "gross_debt": debt,
                "interest_expense": interest,
                "implied_annual_interest_rate": implied_rate,
                "contractual_maturity": cfg["debt_maturities"].get(entity, "2030-12"),
            })
    debt = pd.DataFrame(rows)

    latest_month = months[-1]
    latest = debt[debt.month.eq(latest_month)].copy()
    maturity = latest.groupby("contractual_maturity", as_index=False).gross_debt.sum().rename(columns={"gross_debt": "maturing_debt"})
    maturity["maturity_year"] = maturity.contractual_maturity.str[:4].astype(int)

    monthly_management = management.groupby("month", as_index=False).agg(ebit=("ebit", "sum"), depreciation=("depreciation", "sum"))
    monthly_management["ebitda"] = monthly_management.ebit + monthly_management.depreciation
    group_interest = debt.groupby("month", as_index=False).interest_expense.sum()
    group_cash = journal[journal.account.eq("1000_CASH")].copy()
    group_cash["movement"] = group_cash.debit - group_cash.credit
    group_cash = group_cash.groupby("month", as_index=False).movement.sum().sort_values("month")
    group_cash["cash"] = group_cash.movement.cumsum()
    group_debt = debt.groupby("month", as_index=False).gross_debt.sum()
    liquidity = monthly_management.merge(group_interest, on="month", how="left").merge(group_cash[["month", "cash"]], on="month", how="left").merge(group_debt, on="month", how="left").fillna(0.0)
    liquidity["ebitda_ttm"] = liquidity.ebitda.rolling(12, min_periods=1).sum()
    liquidity["interest_ttm"] = liquidity.interest_expense.rolling(12, min_periods=1).sum()
    liquidity["net_debt"] = liquidity.gross_debt - liquidity.cash
    liquidity["net_leverage"] = liquidity.net_debt / liquidity.ebitda_ttm.replace(0, np.nan)
    liquidity["interest_coverage"] = liquidity.ebitda_ttm / liquidity.interest_ttm.replace(0, np.nan)
    group_minimum_cash = sum(_minimum_cash(entity, cfg) for entity in entities)
    liquidity["minimum_operating_cash"] = group_minimum_cash
    liquidity["rcf_limit"] = cfg["rcf_limit"]
    liquidity["rcf_drawn"] = 0.0
    liquidity["undrawn_rcf"] = liquidity.rcf_limit - liquidity.rcf_drawn
    liquidity["liquidity_headroom"] = (liquidity.cash - liquidity.minimum_operating_cash).clip(lower=0.0) + liquidity.undrawn_rcf
    liquidity["net_leverage_limit"] = cfg["net_leverage_limit"]
    liquidity["interest_coverage_min"] = cfg["interest_coverage_min"]
    liquidity["net_leverage_headroom"] = liquidity.net_leverage_limit - liquidity.net_leverage
    liquidity["interest_coverage_headroom"] = liquidity.interest_coverage - liquidity.interest_coverage_min
    liquidity["covenant_status"] = np.where(
        (liquidity.net_leverage <= liquidity.net_leverage_limit) & (liquidity.interest_coverage >= liquidity.interest_coverage_min),
        "PASS",
        "WATCH",
    )
    return debt.fillna(0.0), maturity.fillna(0.0), liquidity.fillna(0.0)


def treasury_entity_schedule(journal: pd.DataFrame, debt: pd.DataFrame, config: dict) -> pd.DataFrame:
    cfg = _treasury_cfg(config)
    cash = journal[journal.account.eq("1000_CASH")].copy()
    cash["movement"] = cash.debit - cash.credit
    monthly = cash.groupby(["month", "entity"], as_index=False).movement.sum().sort_values(["entity", "month"])
    monthly["cash"] = monthly.groupby("entity").movement.cumsum()
    out = monthly.merge(debt[["month", "entity", "gross_debt", "interest_expense", "implied_annual_interest_rate", "contractual_maturity"]], on=["month", "entity"], how="left").fillna(0.0)
    out["minimum_cash"] = out.entity.map(lambda x: _minimum_cash(str(x), cfg))
    out["cash_above_minimum"] = out.cash - out.minimum_cash
    out["net_debt"] = out.gross_debt - out.cash
    return out


def validate_treasury(base_journal: pd.DataFrame, adjusted_journal: pd.DataFrame, legal_bs: pd.DataFrame, group_bs: pd.DataFrame, debt: pd.DataFrame) -> dict:
    pool = adjusted_journal[adjusted_journal.journal_type.eq("treasury_cash_pool")].copy()
    if pool.empty:
        pool_journal_gap = 0.0
    else:
        by_journal = pool.groupby("journal_id", as_index=False).agg(debit=("debit", "sum"), credit=("credit", "sum"))
        pool_journal_gap = float((by_journal.debit - by_journal.credit).abs().max())

    base_cash = base_journal[base_journal.account.eq("1000_CASH")].copy()
    adjusted_cash = adjusted_journal[adjusted_journal.account.eq("1000_CASH")].copy()
    base_cash["movement"] = base_cash.debit - base_cash.credit
    adjusted_cash["movement"] = adjusted_cash.debit - adjusted_cash.credit
    base_group = base_cash.groupby("month", as_index=False).movement.sum().sort_values("month")
    adjusted_group = adjusted_cash.groupby("month", as_index=False).movement.sum().sort_values("month")
    recon = base_group.merge(adjusted_group, on="month", how="outer", suffixes=("_base", "_pool")).fillna(0.0)
    group_cash_movement_gap = float((recon.movement_base - recon.movement_pool).abs().max()) if not recon.empty else 0.0

    treasury = _treasury_balances(adjusted_journal)
    monthly_treasury = treasury.groupby("month", as_index=False).agg(receivable=("treasury_receivable", "sum"), payable=("treasury_payable", "sum"))
    ic_gap = float((monthly_treasury.receivable - monthly_treasury.payable).abs().max()) if not monthly_treasury.empty else 0.0

    legal_gap = float(legal_bs.balance_check.abs().max()) if not legal_bs.empty else 0.0
    group_gap = float(group_bs.balance_check.abs().max()) if not group_bs.empty else 0.0

    debt_gl = adjusted_journal[adjusted_journal.account.eq("2500_DEBT")].copy()
    debt_gl["movement"] = debt_gl.credit - debt_gl.debit
    debt_gl = debt_gl.groupby(["month", "entity"], as_index=False).movement.sum().sort_values(["entity", "month"])
    debt_gl["gl_debt"] = debt_gl.groupby("entity").movement.cumsum()
    debt_recon = debt.merge(debt_gl[["month", "entity", "gl_debt"]], on=["month", "entity"], how="left").fillna(0.0)
    debt_gap = float((debt_recon.gross_debt - debt_recon.gl_debt).abs().max()) if not debt_recon.empty else 0.0

    checks = {
        "treasury_pool_journal_max_gap": round(pool_journal_gap, 2),
        "treasury_group_cash_movement_max_gap": round(group_cash_movement_gap, 2),
        "treasury_ic_receivable_payable_max_gap": round(ic_gap, 2),
        "treasury_legal_balance_sheet_max_gap": round(legal_gap, 2),
        "treasury_group_balance_sheet_max_gap": round(group_gap, 2),
        "treasury_debt_schedule_max_gap": round(debt_gap, 2),
    }
    checks["passed"] = all(abs(float(v)) <= 0.05 for k, v in checks.items() if k != "passed")
    return checks
