from __future__ import annotations

from collections import defaultdict

import pandas as pd

from .accounting import (
    AccountingResult,
    balance_sheet,
    build_accounting as build_base_accounting,
    cash_flow,
    chart_of_accounts,
    legal_pnl,
    validate_factory_absorption_accounting,
    validate_journal,
)


KEYS = ["month", "entity", "division", "product", "customer"]


def _journal_row(
    *,
    month: str,
    entity: str,
    division: str,
    journal_id: str,
    journal_type: str,
    account: str,
    debit: float = 0.0,
    credit: float = 0.0,
    description: str,
    cash_flow_category: str = "",
) -> dict:
    return {
        "month": month,
        "entity": entity,
        "division": division,
        "journal_id": journal_id,
        "journal_type": journal_type,
        "account": account,
        "debit": round(float(debit), 2),
        "credit": round(float(credit), 2),
        "counterparty": "EXTERNAL",
        "description": description,
        "cash_flow_category": cash_flow_category,
        "product": "",
        "customer": "",
    }


def _opex_lookup(operations: pd.DataFrame) -> dict[tuple[str, str, str, str, str], tuple[float, float]]:
    if "non_people_opex" not in operations.columns or "personnel_cost_allocated" not in operations.columns:
        return {}
    grouped = operations.groupby(KEYS, as_index=False).agg(
        total_opex=("opex", "sum"),
        non_people_opex=("non_people_opex", "sum"),
        personnel_cost=("personnel_cost_allocated", "sum"),
    )
    return {
        tuple(str(getattr(r, key)) for key in KEYS): (
            float(r.non_people_opex),
            float(r.personnel_cost),
        )
        for r in grouped.itertuples(index=False)
    }


def _split_opex_and_remove_supplier_payments(
    journal: pd.DataFrame,
    operations: pd.DataFrame,
) -> pd.DataFrame:
    lookup = _opex_lookup(operations)
    if not lookup:
        return journal.copy()

    # Supplier payments are rebuilt after payroll has been removed from AP accruals.
    out = journal[~journal.journal_type.eq("supplier_payment")].copy()
    opex_mask = out.journal_type.eq("opex")

    for journal_id, idx in out[opex_mask].groupby("journal_id").groups.items():
        group = out.loc[idx]
        first = group.iloc[0]
        key = (
            str(first.month), str(first.entity), str(first.division),
            str(first.product), str(first.customer),
        )
        non_people, _ = lookup.get(key, (float(group.loc[group.account.eq("6000_OPEX"), "debit"].sum()), 0.0))
        amount = round(float(non_people), 2)
        debit_rows = idx[out.loc[idx, "account"].eq("6000_OPEX")]
        credit_rows = idx[out.loc[idx, "account"].eq("2100_AP")]
        if len(debit_rows):
            out.loc[debit_rows, "debit"] = 0.0
            out.loc[debit_rows, "credit"] = 0.0
            out.loc[debit_rows[0], "debit"] = amount
            out.loc[debit_rows, "description"] = "Non-people operating expenses"
        if len(credit_rows):
            out.loc[credit_rows, "debit"] = 0.0
            out.loc[credit_rows, "credit"] = 0.0
            out.loc[credit_rows[0], "credit"] = amount
            out.loc[credit_rows, "description"] = "Non-people operating expense accrual"

    return out


def _append_payroll(journal: pd.DataFrame, operations: pd.DataFrame) -> pd.DataFrame:
    if "personnel_cost_allocated" not in operations.columns:
        return journal.copy()
    payroll = operations.groupby(["month", "entity", "division"], as_index=False).personnel_cost_allocated.sum()
    rows: list[dict] = []
    for r in payroll.itertuples(index=False):
        amount = round(float(r.personnel_cost_allocated), 2)
        if amount <= 0.005:
            continue
        jid = f"PAYROLL-{r.month}-{r.entity}-{str(r.division).replace(' ', '')}"
        rows.append(_journal_row(
            month=str(r.month), entity=str(r.entity), division=str(r.division),
            journal_id=jid, journal_type="payroll", account="6000_OPEX",
            debit=amount, description="Workforce payroll and hiring cost",
        ))
        # The legacy cash-flow engine groups this with operating supplier outflows.
        # The v0.14 workforce schedule separately identifies payroll; importantly,
        # there is no Trade AP entry for personnel cost.
        rows.append(_journal_row(
            month=str(r.month), entity=str(r.entity), division=str(r.division),
            journal_id=jid, journal_type="payroll", account="1000_CASH",
            credit=amount, description="Workforce payroll cash payment",
            cash_flow_category="supplier_payments",
        ))
    if not rows:
        return journal.copy()
    return pd.concat([journal, pd.DataFrame(rows, columns=journal.columns)], ignore_index=True)


def _ap_accruals(journal: pd.DataFrame) -> pd.DataFrame:
    scope = journal[journal.account.eq("2100_AP") & ~journal.journal_type.eq("supplier_payment")].copy()
    if scope.empty:
        return pd.DataFrame(columns=["month", "entity", "division", "accrual"])
    scope["accrual"] = scope.credit.astype(float) - scope.debit.astype(float)
    return scope.groupby(["month", "entity", "division"], as_index=False).accrual.sum()


def _rebuild_supplier_payments(journal: pd.DataFrame, config: dict) -> pd.DataFrame:
    accruals = _ap_accruals(journal)
    if accruals.empty:
        return journal.copy()
    lookup = {
        (str(r.month), str(r.entity), str(r.division)): float(r.accrual)
        for r in accruals.itertuples(index=False)
    }
    months = sorted(str(x) for x in journal.month.unique())
    keys = sorted({(str(r.entity), str(r.division)) for r in accruals.itertuples(index=False)})
    balances: dict[tuple[str, str], float] = defaultdict(float)
    rows: list[dict] = []
    for month in months:
        for entity, division in keys:
            accrual = float(lookup.get((month, entity, division), 0.0))
            available = max(balances[(entity, division)] + accrual, 0.0)
            div_cfg = config["divisions"].get(division, config["divisions"]["Hardware"])
            dpo = float(div_cfg["dpo"])
            target_end = max(accrual, 0.0) * dpo / 30.0
            payment = min(max(available - target_end, 0.0), available)
            if payment > 0.005:
                jid = f"PAY-{month}-{entity}-{division.replace(' ', '')}"
                rows.append(_journal_row(
                    month=month, entity=entity, division=division,
                    journal_id=jid, journal_type="supplier_payment", account="2100_AP",
                    debit=payment, description="Supplier payments",
                ))
                rows.append(_journal_row(
                    month=month, entity=entity, division=division,
                    journal_id=jid, journal_type="supplier_payment", account="1000_CASH",
                    credit=payment, description="Supplier payments",
                    cash_flow_category="supplier_payments",
                ))
            balances[(entity, division)] = available - payment
    if not rows:
        return journal.copy()
    return pd.concat([journal, pd.DataFrame(rows, columns=journal.columns)], ignore_index=True)


def build_accounting(
    config: dict,
    months: pd.PeriodIndex,
    macro: pd.DataFrame,
    operations: pd.DataFrame,
) -> AccountingResult:
    """Build accounting with payroll paid directly and excluded from Trade AP."""
    base = build_base_accounting(config, months, macro, operations)
    if "personnel_cost_allocated" not in operations.columns:
        return base
    journal = _split_opex_and_remove_supplier_payments(base.journal, operations)
    journal = _append_payroll(journal, operations)
    journal = _rebuild_supplier_payments(journal, config)
    return AccountingResult(
        journal=journal,
        capex=base.capex,
        intercompany=base.intercompany,
        factory=base.factory,
    )


def validate_workforce_accounting(journal: pd.DataFrame, operations: pd.DataFrame) -> dict:
    if "personnel_cost_allocated" not in operations.columns:
        return {
            "workforce_payroll_journal_max_gap": 0.0,
            "workforce_payroll_ap_rows": 0,
            "workforce_total_opex_gl_max_gap": 0.0,
            "passed": False,
        }
    payroll_target = operations.groupby(["month", "entity", "division"], as_index=False).personnel_cost_allocated.sum()
    payroll_j = journal[journal.journal_type.eq("payroll") & journal.account.eq("6000_OPEX")].copy()
    payroll_j["payroll_gl"] = payroll_j.debit.astype(float) - payroll_j.credit.astype(float)
    payroll_gl = payroll_j.groupby(["month", "entity", "division"], as_index=False).payroll_gl.sum()
    recon = payroll_target.merge(payroll_gl, on=["month", "entity", "division"], how="outer").fillna(0.0)
    payroll_gap = float((recon.personnel_cost_allocated - recon.payroll_gl).abs().max()) if not recon.empty else 0.0

    ap_payroll = int((journal.journal_type.eq("payroll") & journal.account.eq("2100_AP")).sum())

    target_opex = operations.groupby(["month", "entity", "division"], as_index=False).opex.sum()
    gl = journal[
        journal.account.eq("6000_OPEX") & ~journal.journal_type.eq("closing")
    ].copy()
    gl["opex_gl"] = gl.debit.astype(float) - gl.credit.astype(float)
    gl = gl.groupby(["month", "entity", "division"], as_index=False).opex_gl.sum()
    opex_recon = target_opex.merge(gl, on=["month", "entity", "division"], how="outer").fillna(0.0)
    opex_gap = float((opex_recon.opex - opex_recon.opex_gl).abs().max()) if not opex_recon.empty else 0.0

    return {
        "workforce_payroll_journal_max_gap": round(payroll_gap, 2),
        "workforce_payroll_ap_rows": ap_payroll,
        "workforce_total_opex_gl_max_gap": round(opex_gap, 2),
        "passed": payroll_gap <= 1.0 and ap_payroll == 0 and opex_gap <= 1.0,
    }
