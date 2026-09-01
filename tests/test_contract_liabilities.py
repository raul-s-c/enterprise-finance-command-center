import pandas as pd

from enterprise_finance.accounting import build_accounting, validate_journal
from enterprise_finance.contract_liabilities import (
    apply_contract_liability_accounting,
    group_balance_sheet_with_contracts,
    legal_balance_sheet_with_contracts,
    validate_contract_liabilities,
)
from enterprise_finance.customer_receivables_v10 import build_ar_aging_with_contracts, validate_contract_ar
from enterprise_finance.engine import load_config, month_range
from enterprise_finance.macro import build_macro
from enterprise_finance.model import simulate_operations
from enterprise_finance.provisions import (
    append_provision_journals,
    build_credit_loss_schedule,
    build_inventory_provision_schedule,
)
from enterprise_finance.working_capital_detail import build_ar_aging, build_inventory_aging
from enterprise_finance.accounting import cash_flow


def _fixture(periods=8):
    config = load_config()
    months = month_range("2026-08", periods)
    macro = build_macro(months, int(config["group"]["seed"]), allow_live=False)
    simulation = simulate_operations(config, months, macro)
    accounting = build_accounting(config, months, macro, simulation.operations)
    return config, months, simulation, accounting


def test_customer_advances_create_reconciled_contract_liabilities_without_changing_revenue():
    config, _, simulation, accounting = _fixture(8)
    adjusted, commitments, schedule = apply_contract_liability_accounting(
        accounting.journal, simulation.operations, config
    )

    assert not commitments.empty
    assert not schedule.empty
    assert adjusted.account.eq("2300_CONTRACT_LIABILITIES").any()
    assert adjusted.journal_type.eq("customer_advance").any()
    assert adjusted.journal_type.eq("contract_liability_application").any()

    original_revenue = float(
        accounting.journal.loc[accounting.journal.account.eq("4000_EXTERNAL_REVENUE"), "credit"].sum()
    )
    adjusted_revenue = float(
        adjusted.loc[adjusted.account.eq("4000_EXTERNAL_REVENUE"), "credit"].sum()
    )
    assert abs(original_revenue - adjusted_revenue) <= 0.01

    contract_checks = validate_contract_liabilities(adjusted, schedule)
    assert contract_checks["passed"]
    assert contract_checks["contract_liability_schedule_max_gap"] <= 0.05
    assert contract_checks["contract_liability_journal_max_gap"] <= 0.02

    journal_checks = validate_journal(adjusted)
    assert journal_checks["journal_balance_max_gap"] <= 0.02
    assert journal_checks["trial_balance_gap"] <= 0.02


def test_contract_aware_ar_reconciles_and_reduces_credit_exposure():
    config, _, simulation, accounting = _fixture(8)
    adjusted, _, schedule = apply_contract_liability_accounting(
        accounting.journal, simulation.operations, config
    )
    contract_ar = build_ar_aging_with_contracts(adjusted, simulation.customers, config)
    base_ar = build_ar_aging(accounting.journal, simulation.customers, config)

    ar_checks = validate_contract_ar(adjusted, contract_ar)
    assert ar_checks["passed"]
    assert ar_checks["contract_ar_subledger_max_gap"] <= 0.05

    end_month = "2026-08"
    contract_ar_end = float(contract_ar.loc[contract_ar.month.eq(end_month), "total_ar"].sum())
    base_ar_end = float(base_ar.loc[base_ar.month.eq(end_month), "total_ar"].sum())
    assert contract_ar_end < base_ar_end

    base_ecl = build_credit_loss_schedule(base_ar, config)
    contract_ecl = build_credit_loss_schedule(contract_ar, config)
    base_allowance = float(base_ecl.loc[base_ecl.month.eq(end_month), "credit_loss_allowance"].sum())
    contract_allowance = float(contract_ecl.loc[contract_ecl.month.eq(end_month), "credit_loss_allowance"].sum())
    assert contract_allowance <= base_allowance

    latest_contract = schedule[schedule.month.eq(end_month)]
    assert float(latest_contract.contract_liability.sum()) > 0


def test_contract_liabilities_keep_balance_sheet_and_cash_reconciled_after_provisions():
    config, _, simulation, accounting = _fixture(8)
    adjusted, _, schedule = apply_contract_liability_accounting(
        accounting.journal, simulation.operations, config
    )
    ar_aging = build_ar_aging_with_contracts(adjusted, simulation.customers, config)
    inventory_aging = build_inventory_aging(
        adjusted, simulation.operations, simulation.products, config
    )
    ecl = build_credit_loss_schedule(ar_aging, config)
    inv_prov = build_inventory_provision_schedule(inventory_aging, config)
    journal, _ = append_provision_journals(adjusted, ecl, inv_prov)

    legal_bs = legal_balance_sheet_with_contracts(journal)
    group_bs = group_balance_sheet_with_contracts(
        legal_bs, float(config["transfer_pricing"]["manufacturing_cost_plus"])
    )
    assert float(legal_bs.balance_check.abs().max()) <= 0.05
    assert float(group_bs.balance_check.abs().max()) <= 0.05

    contract_checks = validate_contract_liabilities(journal, schedule)
    assert contract_checks["passed"]

    cf = cash_flow(journal)
    cash_movement = cf.groupby("entity", as_index=False).net_cash_movement.sum()
    ending = legal_bs[legal_bs.month.eq("2026-08")][["entity", "cash"]]
    recon = ending.merge(cash_movement, on="entity", how="left").fillna(0.0)
    assert float((recon.cash - recon.net_cash_movement).abs().max()) <= 0.05
