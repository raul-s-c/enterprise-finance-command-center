import pandas as pd

from enterprise_finance.fx_translation import (
    build_translation_schedule,
    constant_currency_analysis,
    enrich_journal_with_functional_currency,
    local_trial_balance,
    validate_fx_translation,
)


def _config():
    return {
        "entities": [
            {"code": "DE01", "currency": "EUR"},
            {"code": "US01", "currency": "USD"},
        ]
    }


def _macro():
    return pd.DataFrame([
        {"month": "2026-01", "EUR": 1.0, "USD": 0.91},
        {"month": "2026-02", "EUR": 1.0, "USD": 0.94},
    ])


def _journal():
    return pd.DataFrame([
        {"month": "2026-01", "entity": "US01", "journal_id": "OPEN-US", "account": "1000_CASH", "debit": 1000.0, "credit": 0.0},
        {"month": "2026-01", "entity": "US01", "journal_id": "OPEN-US", "account": "3000_SHARE_CAPITAL", "debit": 0.0, "credit": 1000.0},
        {"month": "2026-02", "entity": "US01", "journal_id": "SALE-US", "account": "1100_AR", "debit": 940.0, "credit": 0.0},
        {"month": "2026-02", "entity": "US01", "journal_id": "SALE-US", "account": "4000_EXTERNAL_REVENUE", "debit": 0.0, "credit": 940.0},
        {"month": "2026-02", "entity": "US01", "journal_id": "CLOSE-US", "account": "4000_EXTERNAL_REVENUE", "debit": 940.0, "credit": 0.0},
        {"month": "2026-02", "entity": "US01", "journal_id": "CLOSE-US", "account": "3200_RETAINED_EARNINGS", "debit": 0.0, "credit": 940.0},
    ])


def _chart():
    return pd.DataFrame([
        {"account": "1000_CASH", "statement": "Balance Sheet", "account_type": "Asset"},
        {"account": "1100_AR", "statement": "Balance Sheet", "account_type": "Asset"},
        {"account": "3000_SHARE_CAPITAL", "statement": "Balance Sheet", "account_type": "Equity"},
        {"account": "3200_RETAINED_EARNINGS", "statement": "Balance Sheet", "account_type": "Equity"},
        {"account": "4000_EXTERNAL_REVENUE", "statement": "P&L", "account_type": "Revenue"},
    ])


def test_functional_currency_journal_and_translation_reserve():
    local = enrich_journal_with_functional_currency(_journal(), _macro(), _config())
    assert set(local.functional_currency) == {"USD"}
    assert local.fx_to_eur.min() > 0
    journal_balance = local.groupby("journal_id").agg(debit=("local_debit", "sum"), credit=("local_credit", "sum"))
    assert (journal_balance.debit - journal_balance.credit).abs().max() <= 0.01

    trial = local_trial_balance(local)
    assert not trial.empty
    translation = build_translation_schedule(local, _macro(), _config(), _chart())
    assert not translation.empty
    controls = validate_fx_translation(local, translation)
    assert controls["passed"], controls
    assert controls["functional_currency_journal_max_gap"] == 0.0
    assert controls["fx_translation_balance_max_gap"] == 0.0

    feb = translation[translation.month.eq("2026-02")].iloc[0]
    assert abs(feb.translated_share_capital - 1000.0) <= 0.02
    assert abs(feb.translated_retained_earnings - 940.0) <= 0.02
    assert abs(feb.fx_translation_reserve) > 0.0
    assert feb.translation_balance_check == 0.0
    assert feb.closing_fx_to_eur == 0.94
    assert feb.historical_equity_fx_to_eur == 0.91


def test_constant_currency_separates_fx_effect():
    management = pd.DataFrame([
        {"month": "2026-02", "entity": "US01", "division": "Software", "revenue": 940.0, "ebit": 188.0},
        {"month": "2026-02", "entity": "DE01", "division": "Software", "revenue": 500.0, "ebit": 100.0},
    ])
    macro = pd.DataFrame([
        {"month": "2025-02", "EUR": 1.0, "USD": 0.90},
        {"month": "2026-02", "EUR": 1.0, "USD": 0.94},
    ])
    cc = constant_currency_analysis(management, macro, _config(), "2026-02")
    usd = cc[cc.entity.eq("US01")].iloc[0]
    eur = cc[cc.entity.eq("DE01")].iloc[0]
    assert usd.reported_revenue == 940.0
    assert usd.constant_currency_revenue == 900.0
    assert usd.revenue_fx_effect == 40.0
    assert eur.revenue_fx_effect == 0.0
