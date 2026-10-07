import pandas as pd

from enterprise_finance.engine_v12 import _capital_allocation, _scenario_summary as liquidity_summary
from enterprise_finance.engine_v13 import _scenario_summary as statement_summary


def test_liquidity_summary_keeps_12m_and_24m_endpoints_distinct():
    rows = []
    for horizon in range(1, 25):
        rows.append({
            "scenario": "Base", "horizon_month": horizon,
            "ending_cash": float(horizon), "gross_debt": 100.0,
            "net_debt": 100.0 - horizon, "liquidity_headroom": 200.0 - horizon,
            "deployable_cash": float(horizon), "net_leverage": float(horizon) / 10,
            "interest_coverage": 3.0, "undrawn_rcf": 500.0,
            "covenant_status": "Compliant", "rcf_drawn": 0.0,
            "capex": 1.0, "operating_cash_flow": 2.0,
            "scheduled_debt_repayment": 0.5,
        })
    summary = liquidity_summary(pd.DataFrame(rows)).iloc[0]
    assert summary.ending_cash_12m == 12
    assert summary.ending_cash_24m == 24
    assert summary.forecast_capex_12m == 12
    assert summary.forecast_capex_24m == 24
    allocation = _capital_allocation(pd.DataFrame(rows), {"treasury": {"strategic_liquidity_buffer": 15.0}})
    assert "downside_protected_allocation_capacity_24m" in allocation.columns


def test_statement_summary_keeps_12m_and_24m_flows_and_balances_distinct():
    rows = []
    for horizon in range(1, 25):
        rows.append({"scenario": "Base", "horizon_month": horizon, "revenue": 10.0,
                     "ebit": 2.0, "net_income": 1.0})
    pnl = pd.DataFrame(rows)
    rows = []
    for horizon in range(1, 25):
        rows.append({"scenario": "Base", "horizon_month": horizon, "cash": float(horizon),
                     "trade_receivables": 3.0, "inventory": 4.0, "debt": 5.0,
                     "contract_liabilities": 6.0, "assets": 100.0 + horizon,
                     "liabilities": 40.0, "equity": 60.0 + horizon,
                     "balance_check": 0.0})
    bs = pd.DataFrame(rows)
    cf = pd.DataFrame({"scenario": "Base", "horizon_month": range(1, 25),
                       "operating_cash_flow": [3.0] * 24, "free_cash_flow": [2.0] * 24})
    summary = statement_summary(pnl, bs, cf).iloc[0]
    assert summary.revenue_12m == 120.0
    assert summary.revenue_24m == 240.0
    assert summary.ending_cash_12m == 12.0
    assert summary.ending_cash_24m == 24.0
