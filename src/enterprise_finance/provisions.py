from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from .accounting import balance_sheet, chart_of_accounts, legal_pnl
from .factory_absorption import management_pnl_with_factory_absorption


AR_ALLOWANCE_ACCOUNT = "1190_CREDIT_LOSS_ALLOWANCE"
INVENTORY_ALLOWANCE_ACCOUNT = "1290_INVENTORY_PROVISION"
INVENTORY_EXPENSE_ACCOUNT = "5460_INVENTORY_OBSOLESCENCE"
CREDIT_LOSS_EXPENSE_ACCOUNT = "6050_CREDIT_LOSS_EXPENSE"

PROVISION_ACCOUNT_META = {
    AR_ALLOWANCE_ACCOUNT: ("Balance Sheet", "Credit Loss Allowance", "Contra Asset"),
    INVENTORY_ALLOWANCE_ACCOUNT: ("Balance Sheet", "Inventory Obsolescence Provision", "Contra Asset"),
    INVENTORY_EXPENSE_ACCOUNT: ("P&L", "Inventory Obsolescence Expense", "Expense"),
    CREDIT_LOSS_EXPENSE_ACCOUNT: ("P&L", "Expected Credit Loss Expense", "Expense"),
}

DEFAULT_ECL_RATES = {
    "current": 0.002,
    "overdue_1_30": 0.010,
    "overdue_31_60": 0.040,
    "overdue_61_90": 0.120,
    "overdue_90_plus": 0.450,
}

DEFAULT_INVENTORY_RATES = {
    "age_0_30": 0.000,
    "age_31_60": 0.005,
    "age_61_90": 0.020,
    "age_91_180": 0.120,
    "age_180_plus": 0.550,
}


def chart_of_accounts_with_provisions() -> pd.DataFrame:
    base = chart_of_accounts()
    extra = pd.DataFrame([
        {"account": account, "statement": meta[0], "line": meta[1], "account_type": meta[2]}
        for account, meta in PROVISION_ACCOUNT_META.items()
    ])
    return pd.concat([base, extra], ignore_index=True).drop_duplicates("account", keep="last")


def _provision_config(config: dict) -> dict:
    return config.get("provisions", {})


def build_credit_loss_schedule(ar_aging: pd.DataFrame, config: dict) -> pd.DataFrame:
    if ar_aging.empty:
        return pd.DataFrame(columns=[
            "month", "entity", "division", "customer", "customer_name", "risk_score",
            "gross_ar", "credit_loss_allowance", "net_ar", "allowance_pct",
        ])
    cfg = _provision_config(config)
    rates = {**DEFAULT_ECL_RATES, **cfg.get("credit_loss_rates", {})}
    risk_min = float(cfg.get("credit_risk_multiplier_min", 0.70))
    risk_max = float(cfg.get("credit_risk_multiplier_max", 1.35))

    out = ar_aging.copy()
    normalized_risk = ((out.risk_score.astype(float) - 1.0) / 4.0).clip(0.0, 1.0)
    out["risk_multiplier"] = risk_min + normalized_risk * (risk_max - risk_min)
    component_cols: list[str] = []
    for bucket, rate in rates.items():
        if bucket not in out.columns:
            out[bucket] = 0.0
        col = f"ecl_{bucket}"
        out[col] = out[bucket].astype(float) * float(rate) * out.risk_multiplier
        component_cols.append(col)
    out["gross_ar"] = out.total_ar.astype(float)
    out["credit_loss_allowance"] = out[component_cols].sum(axis=1).clip(lower=0.0)
    out["credit_loss_allowance"] = np.minimum(out.credit_loss_allowance, out.gross_ar)
    out["net_ar"] = out.gross_ar - out.credit_loss_allowance
    out["allowance_pct"] = out.credit_loss_allowance / out.gross_ar.replace(0, np.nan)
    return out.fillna(0.0)


def build_inventory_provision_schedule(inventory_aging: pd.DataFrame, config: dict) -> pd.DataFrame:
    if inventory_aging.empty:
        return pd.DataFrame(columns=[
            "month", "entity", "division", "product", "product_family", "generation",
            "gross_inventory", "inventory_provision", "net_inventory", "provision_pct",
        ])
    cfg = _provision_config(config)
    rates = {**DEFAULT_INVENTORY_RATES, **cfg.get("inventory_provision_rates", {})}
    legacy_multiplier = float(cfg.get("legacy_inventory_multiplier", 1.25))
    spare_parts_multiplier = float(cfg.get("spare_parts_inventory_multiplier", 0.85))
    premium_multiplier = float(cfg.get("premium_inventory_multiplier", 1.10))

    out = inventory_aging.copy()
    out["inventory_risk_multiplier"] = 1.0
    out.loc[out.generation.eq("Legacy"), "inventory_risk_multiplier"] *= legacy_multiplier
    out.loc[out.division.eq("Spare Parts"), "inventory_risk_multiplier"] *= spare_parts_multiplier
    out.loc[out.quality_tier.eq("Premium"), "inventory_risk_multiplier"] *= premium_multiplier

    component_cols: list[str] = []
    for bucket, rate in rates.items():
        if bucket not in out.columns:
            out[bucket] = 0.0
        col = f"provision_{bucket}"
        out[col] = out[bucket].astype(float) * float(rate) * out.inventory_risk_multiplier
        component_cols.append(col)
    out["gross_inventory"] = out.inventory_value.astype(float)
    out["inventory_provision"] = out[component_cols].sum(axis=1).clip(lower=0.0)
    out["inventory_provision"] = np.minimum(out.inventory_provision, out.gross_inventory)
    out["net_inventory"] = out.gross_inventory - out.inventory_provision
    out["provision_pct"] = out.inventory_provision / out.gross_inventory.replace(0, np.nan)
    return out.fillna(0.0)


def _grid_targets(schedule: pd.DataFrame, target_col: str, months: list[str]) -> pd.DataFrame:
    if schedule.empty:
        return pd.DataFrame(columns=["month", "entity", "division", target_col])
    summary = schedule.groupby(["month", "entity", "division"], as_index=False)[target_col].sum()
    keys = summary[["entity", "division"]].drop_duplicates()
    grid = keys.merge(pd.DataFrame({"month": months}), how="cross")
    return grid.merge(summary, on=["month", "entity", "division"], how="left").fillna({target_col: 0.0})


def _row(*, month: str, entity: str, division: str, journal_id: str, journal_type: str, account: str, debit: float = 0.0, credit: float = 0.0, description: str = "") -> dict:
    return {
        "month": month,
        "entity": entity,
        "division": division,
        "journal_id": journal_id,
        "journal_type": journal_type,
        "account": account,
        "debit": round(float(debit), 2),
        "credit": round(float(credit), 2),
        "counterparty": "PROVISION",
        "description": description,
        "cash_flow_category": "",
        "product": "",
        "customer": "",
    }


def _append_target_movements(
    rows: list[dict],
    target_grid: pd.DataFrame,
    target_col: str,
    allowance_account: str,
    expense_account: str,
    prefix: str,
    description: str,
) -> None:
    previous: dict[tuple[str, str], float] = defaultdict(float)
    for r in target_grid.sort_values(["month", "entity", "division"]).itertuples(index=False):
        key = (str(r.entity), str(r.division))
        target = float(getattr(r, target_col))
        movement = target - previous[key]
        previous[key] = target
        if abs(movement) <= 0.005:
            continue
        jid = f"{prefix}-{r.month}-{r.entity}-{str(r.division).replace(' ', '')}"
        close_id = f"{prefix}CLOSE-{r.month}-{r.entity}-{str(r.division).replace(' ', '')}"
        if movement > 0:
            rows.append(_row(month=str(r.month), entity=str(r.entity), division=str(r.division), journal_id=jid, journal_type="provision", account=expense_account, debit=movement, description=description))
            rows.append(_row(month=str(r.month), entity=str(r.entity), division=str(r.division), journal_id=jid, journal_type="provision", account=allowance_account, credit=movement, description=description))
            rows.append(_row(month=str(r.month), entity=str(r.entity), division=str(r.division), journal_id=close_id, journal_type="closing", account=expense_account, credit=movement, description=f"Close {description}"))
            rows.append(_row(month=str(r.month), entity=str(r.entity), division=str(r.division), journal_id=close_id, journal_type="closing", account="3200_RETAINED_EARNINGS", debit=movement, description=f"Close {description}"))
        else:
            release = -movement
            rows.append(_row(month=str(r.month), entity=str(r.entity), division=str(r.division), journal_id=jid, journal_type="provision_release", account=allowance_account, debit=release, description=f"Release {description}"))
            rows.append(_row(month=str(r.month), entity=str(r.entity), division=str(r.division), journal_id=jid, journal_type="provision_release", account=expense_account, credit=release, description=f"Release {description}"))
            rows.append(_row(month=str(r.month), entity=str(r.entity), division=str(r.division), journal_id=close_id, journal_type="closing", account=expense_account, debit=release, description=f"Close release {description}"))
            rows.append(_row(month=str(r.month), entity=str(r.entity), division=str(r.division), journal_id=close_id, journal_type="closing", account="3200_RETAINED_EARNINGS", credit=release, description=f"Close release {description}"))


def append_provision_journals(
    journal: pd.DataFrame,
    credit_loss_schedule: pd.DataFrame,
    inventory_provision_schedule: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    months = sorted(journal.month.unique())
    ecl_grid = _grid_targets(credit_loss_schedule, "credit_loss_allowance", months)
    inv_grid = _grid_targets(inventory_provision_schedule, "inventory_provision", months)
    new_rows: list[dict] = []
    _append_target_movements(
        new_rows, ecl_grid, "credit_loss_allowance", AR_ALLOWANCE_ACCOUNT,
        CREDIT_LOSS_EXPENSE_ACCOUNT, "ECL", "Expected credit loss allowance",
    )
    _append_target_movements(
        new_rows, inv_grid, "inventory_provision", INVENTORY_ALLOWANCE_ACCOUNT,
        INVENTORY_EXPENSE_ACCOUNT, "INVPROV", "Inventory obsolescence provision",
    )
    provision_journal = pd.DataFrame(new_rows, columns=journal.columns)
    if provision_journal.empty:
        return journal.copy(), provision_journal
    return pd.concat([journal, provision_journal], ignore_index=True), provision_journal


def legal_pnl_with_provisions(journal: pd.DataFrame) -> pd.DataFrame:
    base = legal_pnl(journal).copy()
    scope = journal[
        journal.account.isin([INVENTORY_EXPENSE_ACCOUNT, CREDIT_LOSS_EXPENSE_ACCOUNT])
        & ~journal.journal_type.eq("closing")
    ].copy()
    if scope.empty:
        base["inventory_provision_expense"] = 0.0
        base["credit_loss_expense"] = 0.0
        return base
    scope["amount"] = scope.debit - scope.credit
    prov = scope.pivot_table(
        index=["month", "entity", "division"], columns="account", values="amount", aggfunc="sum", fill_value=0.0
    ).reset_index()
    for account in [INVENTORY_EXPENSE_ACCOUNT, CREDIT_LOSS_EXPENSE_ACCOUNT]:
        if account not in prov.columns:
            prov[account] = 0.0
    prov = prov.rename(columns={
        INVENTORY_EXPENSE_ACCOUNT: "inventory_provision_expense",
        CREDIT_LOSS_EXPENSE_ACCOUNT: "credit_loss_expense",
    })
    out = base.merge(prov, on=["month", "entity", "division"], how="outer")
    for col in base.columns:
        if col not in {"month", "entity", "division"}:
            out[col] = out[col].fillna(0.0)
    out[["inventory_provision_expense", "credit_loss_expense"]] = out[["inventory_provision_expense", "credit_loss_expense"]].fillna(0.0)
    out["cogs"] = out.cogs + out.inventory_provision_expense
    out["gross_profit"] = out.gross_profit - out.inventory_provision_expense
    out["ebit"] = out.ebit - out.inventory_provision_expense - out.credit_loss_expense
    out["ebt"] = out.ebt - out.inventory_provision_expense - out.credit_loss_expense
    out["net_income"] = out.net_income - out.inventory_provision_expense - out.credit_loss_expense
    return out


def _contra_balances(journal: pd.DataFrame) -> pd.DataFrame:
    scope = journal[journal.account.isin([AR_ALLOWANCE_ACCOUNT, INVENTORY_ALLOWANCE_ACCOUNT])].copy()
    if scope.empty:
        return pd.DataFrame(columns=["month", "entity", "credit_loss_allowance", "inventory_provision"])
    scope["signed"] = scope.debit - scope.credit
    monthly = scope.groupby(["month", "entity", "account"], as_index=False).signed.sum()
    months = sorted(journal.month.unique())
    entities = sorted(journal.entity.unique())
    cumulative: dict[tuple[str, str], float] = defaultdict(float)
    rows: list[dict] = []
    for month in months:
        m = monthly[monthly.month.eq(month)]
        for r in m.itertuples(index=False):
            cumulative[(str(r.entity), str(r.account))] += float(r.signed)
        for entity in entities:
            rows.append({
                "month": month,
                "entity": entity,
                "credit_loss_allowance": -cumulative[(entity, AR_ALLOWANCE_ACCOUNT)],
                "inventory_provision": -cumulative[(entity, INVENTORY_ALLOWANCE_ACCOUNT)],
            })
    return pd.DataFrame(rows)


def legal_balance_sheet_with_provisions(journal: pd.DataFrame) -> pd.DataFrame:
    base = balance_sheet(journal).copy()
    contra = _contra_balances(journal)
    out = base.merge(contra, on=["month", "entity"], how="left").fillna({
        "credit_loss_allowance": 0.0,
        "inventory_provision": 0.0,
    })
    out["trade_receivables_gross"] = out.trade_receivables
    out["inventory_gross"] = out.inventory
    out["trade_receivables"] = out.trade_receivables_gross - out.credit_loss_allowance
    out["inventory"] = out.inventory_gross - out.inventory_provision
    out["assets"] = out.assets - out.credit_loss_allowance - out.inventory_provision
    out["balance_check"] = out.assets - out.liabilities - out.equity
    return out


def group_balance_sheet_with_provisions(legal_bs: pd.DataFrame, markup: float) -> pd.DataFrame:
    rows: list[dict] = []
    for month, grp in legal_bs.groupby("month"):
        cash = float(grp.cash.sum())
        ar_gross = float(grp.trade_receivables_gross.sum())
        ecl = float(grp.credit_loss_allowance.sum())
        ar = ar_gross - ecl
        inventory_gross = float(grp.inventory_gross.sum())
        inventory_provision = float(grp.inventory_provision.sum())
        unrealized_markup = max(inventory_gross, 0.0) * markup / (1.0 + markup)
        inventory = inventory_gross - inventory_provision - unrealized_markup
        ppe_gross = float(grp.ppe_gross.sum())
        cip = float(grp.cip.sum())
        accum_dep = float(grp.accumulated_depreciation.sum())
        ap = float(grp.trade_payables.sum())
        tax_payable = float(grp.tax_payable.sum())
        debt = float(grp.debt.sum())
        share_capital = float(grp.share_capital.sum())
        retained = float(grp.retained_earnings.sum()) - unrealized_markup
        assets = cash + ar + inventory + ppe_gross + cip + accum_dep
        liabilities = ap + tax_payable + debt
        equity = share_capital + retained
        rows.append({
            "month": month,
            "cash": cash,
            "trade_receivables_gross": ar_gross,
            "credit_loss_allowance": ecl,
            "trade_receivables": ar,
            "inventory_gross": inventory_gross,
            "inventory_provision": inventory_provision,
            "inventory_legal_transfer_value": inventory_gross,
            "unrealized_ic_markup_reserve": unrealized_markup,
            "inventory": inventory,
            "ppe_gross": ppe_gross,
            "cip": cip,
            "accumulated_depreciation": accum_dep,
            "trade_payables": ap,
            "tax_payable": tax_payable,
            "debt": debt,
            "share_capital": share_capital,
            "retained_earnings": retained,
            "assets": assets,
            "liabilities": liabilities,
            "equity": equity,
            "balance_check": assets - liabilities - equity,
        })
    return pd.DataFrame(rows)


def management_pnl_with_provisions(
    operations: pd.DataFrame,
    journal: pd.DataFrame,
    factory_entities: list[str] | set[str],
) -> pd.DataFrame:
    base = management_pnl_with_factory_absorption(operations, journal, factory_entities).copy()
    base["inventory_provision_expense"] = 0.0
    base["credit_loss_expense"] = 0.0
    scope = journal[
        journal.account.isin([INVENTORY_EXPENSE_ACCOUNT, CREDIT_LOSS_EXPENSE_ACCOUNT])
        & ~journal.journal_type.eq("closing")
    ].copy()
    if scope.empty:
        return base
    scope["amount"] = scope.debit - scope.credit
    pivot = scope.pivot_table(
        index=["month", "entity", "division"], columns="account", values="amount", aggfunc="sum", fill_value=0.0
    ).reset_index()
    for account in [INVENTORY_EXPENSE_ACCOUNT, CREDIT_LOSS_EXPENSE_ACCOUNT]:
        if account not in pivot.columns:
            pivot[account] = 0.0
    rows: list[dict] = []
    for _, r in pivot.iterrows():
        inv_expense = float(r[INVENTORY_EXPENSE_ACCOUNT])
        ecl_expense = float(r[CREDIT_LOSS_EXPENSE_ACCOUNT])
        rows.append({
            "month": str(r["month"]),
            "entity": str(r["entity"]),
            "division": str(r["division"]),
            "revenue": 0.0,
            "variable_production_cost": 0.0,
            "variable_selling_cost": 0.0,
            "fixed_production_cost": inv_expense,
            "marginal_contribution": 0.0,
            "gross_profit": -inv_expense,
            "opex": ecl_expense,
            "depreciation": 0.0,
            "ebit": -inv_expense - ecl_expense,
            "interest": 0.0,
            "ebt": -inv_expense - ecl_expense,
            "tax": 0.0,
            "net_income": -inv_expense - ecl_expense,
            "factory_absorption_variance": 0.0,
            "inventory_provision_expense": inv_expense,
            "credit_loss_expense": ecl_expense,
        })
    return pd.concat([base, pd.DataFrame(rows)], ignore_index=True, sort=False).fillna(0.0)


def _allowance_gl_by_division(journal: pd.DataFrame, account: str, output: str) -> pd.DataFrame:
    scope = journal[journal.account.eq(account)].copy()
    if scope.empty:
        return pd.DataFrame(columns=["month", "entity", "division", output])
    scope["movement"] = scope.debit - scope.credit
    monthly = scope.groupby(["month", "entity", "division"], as_index=False).movement.sum()
    months = sorted(journal.month.unique())
    keys = [(str(e), str(d)) for e, d in monthly[["entity", "division"]].drop_duplicates().itertuples(index=False, name=None)]
    cumulative: dict[tuple[str, str], float] = defaultdict(float)
    rows: list[dict] = []
    for month in months:
        m = monthly[monthly.month.eq(month)]
        for r in m.itertuples(index=False):
            cumulative[(str(r.entity), str(r.division))] += float(r.movement)
        for entity, division in keys:
            rows.append({"month": month, "entity": entity, "division": division, output: -cumulative[(entity, division)]})
    return pd.DataFrame(rows)


def validate_provisions(
    journal: pd.DataFrame,
    credit_loss_schedule: pd.DataFrame,
    inventory_provision_schedule: pd.DataFrame,
) -> dict:
    ecl_target = credit_loss_schedule.groupby(["month", "entity", "division"], as_index=False).agg(
        target_allowance=("credit_loss_allowance", "sum"), gross_ar=("gross_ar", "sum")
    ) if not credit_loss_schedule.empty else pd.DataFrame(columns=["month", "entity", "division", "target_allowance", "gross_ar"])
    ecl_gl = _allowance_gl_by_division(journal, AR_ALLOWANCE_ACCOUNT, "gl_allowance")
    ecl_recon = ecl_target.merge(ecl_gl, on=["month", "entity", "division"], how="outer").fillna(0.0)
    ecl_gap = float((ecl_recon.target_allowance - ecl_recon.gl_allowance).abs().max()) if not ecl_recon.empty else 0.0
    ecl_excess = float((ecl_recon.target_allowance - ecl_recon.gross_ar).clip(lower=0.0).max()) if not ecl_recon.empty else 0.0

    inv_target = inventory_provision_schedule.groupby(["month", "entity", "division"], as_index=False).agg(
        target_provision=("inventory_provision", "sum"), gross_inventory=("gross_inventory", "sum")
    ) if not inventory_provision_schedule.empty else pd.DataFrame(columns=["month", "entity", "division", "target_provision", "gross_inventory"])
    inv_gl = _allowance_gl_by_division(journal, INVENTORY_ALLOWANCE_ACCOUNT, "gl_provision")
    inv_recon = inv_target.merge(inv_gl, on=["month", "entity", "division"], how="outer").fillna(0.0)
    inv_gap = float((inv_recon.target_provision - inv_recon.gl_provision).abs().max()) if not inv_recon.empty else 0.0
    inv_excess = float((inv_recon.target_provision - inv_recon.gross_inventory).clip(lower=0.0).max()) if not inv_recon.empty else 0.0

    checks = {
        "credit_loss_allowance_max_gap": round(ecl_gap, 2),
        "credit_loss_allowance_excess_max": round(ecl_excess, 2),
        "inventory_provision_max_gap": round(inv_gap, 2),
        "inventory_provision_excess_max": round(inv_excess, 2),
    }
    checks["passed"] = all(abs(float(v)) <= 0.05 for v in checks.values())
    return checks


def provision_monthly_summary(
    credit_loss_schedule: pd.DataFrame,
    inventory_provision_schedule: pd.DataFrame,
    journal: pd.DataFrame,
) -> pd.DataFrame:
    ecl = credit_loss_schedule.groupby("month", as_index=False).agg(
        gross_ar=("gross_ar", "sum"), credit_loss_allowance=("credit_loss_allowance", "sum"), net_ar=("net_ar", "sum")
    ) if not credit_loss_schedule.empty else pd.DataFrame(columns=["month", "gross_ar", "credit_loss_allowance", "net_ar"])
    inv = inventory_provision_schedule.groupby("month", as_index=False).agg(
        gross_inventory=("gross_inventory", "sum"), inventory_provision=("inventory_provision", "sum"), net_inventory=("net_inventory", "sum")
    ) if not inventory_provision_schedule.empty else pd.DataFrame(columns=["month", "gross_inventory", "inventory_provision", "net_inventory"])
    exp = journal[
        journal.account.isin([INVENTORY_EXPENSE_ACCOUNT, CREDIT_LOSS_EXPENSE_ACCOUNT])
        & ~journal.journal_type.eq("closing")
    ].copy()
    if exp.empty:
        expenses = pd.DataFrame(columns=["month", "credit_loss_expense", "inventory_provision_expense"])
    else:
        exp["amount"] = exp.debit - exp.credit
        expenses = exp.pivot_table(index="month", columns="account", values="amount", aggfunc="sum", fill_value=0.0).reset_index()
        for account in [INVENTORY_EXPENSE_ACCOUNT, CREDIT_LOSS_EXPENSE_ACCOUNT]:
            if account not in expenses.columns:
                expenses[account] = 0.0
        expenses = expenses.rename(columns={
            INVENTORY_EXPENSE_ACCOUNT: "inventory_provision_expense",
            CREDIT_LOSS_EXPENSE_ACCOUNT: "credit_loss_expense",
        })
    return ecl.merge(inv, on="month", how="outer").merge(expenses, on="month", how="outer").fillna(0.0).sort_values("month")
