import pandas as pd
import pytest

from enterprise_finance.accounting import _capex_schedule
from enterprise_finance.capex import capex_spend_schedule
from enterprise_finance.liquidity_forecast import future_capex
from enterprise_finance.three_statement_forecast import _capex_project_schedules


@pytest.fixture
def project_config():
    project = {
        "id": "CAPEX-ROUNDING-01",
        "name": "Precision test project",
        "entity": "CZ01",
        "division": "Hardware",
        "budget": 6_200_000.0,
        "start": "2025-02",
        "build_months": 10,
        "useful_life_months": 96,
        "capacity_increase_pct": 0.16,
    }
    return {"capex_projects": [project], "factories": {}}


def test_installments_sum_to_approved_budget_at_ledger_cent_precision(project_config):
    project = project_config["capex_projects"][0]

    schedule = capex_spend_schedule(project)

    assert sum(schedule.values()) == pytest.approx(project["budget"], abs=0.001)
    assert all(amount >= 0 for amount in schedule.values())
    assert len(schedule) == project["build_months"]


def test_accounting_liquidity_and_three_statement_forecasts_share_same_schedule(project_config):
    project = project_config["capex_projects"][0]
    expected = capex_spend_schedule(project)
    months = pd.period_range(project["start"], periods=project["build_months"], freq="M")

    accounting_events, _ = _capex_schedule(project_config, months)
    accounting = (
        accounting_events.loc[
            accounting_events.project.eq(project["id"]) & accounting_events.event.eq("SPEND")
        ]
        .set_index("month")
        .amount
        .astype(float)
        .to_dict()
    )
    liquidity = future_capex(
        project_config,
        str(pd.Period(project["start"], freq="M") - 1),
        horizon=project["build_months"],
    )
    liquidity = (
        liquidity.loc[liquidity.project.eq(project["id"])]
        .set_index("month")
        .capex
        .astype(float)
        .to_dict()
    )
    forecast, _ = _capex_project_schedules(
        project_config,
        str(pd.Period(project["start"], freq="M") - 1),
        opening_cip=0.0,
    )

    assert accounting == expected
    assert liquidity == expected
    assert forecast[project["id"]]["spends"] == expected
