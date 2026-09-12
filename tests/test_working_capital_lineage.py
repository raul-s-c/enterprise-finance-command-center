import pandas as pd
import pytest

from enterprise_finance.working_capital_lineage import build_working_capital_lineage


def source():
    return pd.DataFrame([
        dict(month=m, entity="ES01", division="Hardware", account=a,
             journal_id=j, journal_type=t, debit=d, credit=c)
        for m, a, j, t, d, c in [
            ("2026-01", "1100_AR", "SALE-1", "sale", 100, 0),
            ("2026-03", "1100_AR", "CASH-1", "collection", 0, 35),
            ("2026-03", "2100_AP", "ACCRUAL-1", "opex", 0, 20),
            ("2026-04", "1100_AR", "FUTURE", "sale", 999, 0),
        ]
    ])


def test_postings_preserve_identity_and_signed_rollforward():
    journal = source()
    before = journal.copy(deep=True)
    detail, history, checks = build_working_capital_lineage(journal, "2026-03")
    assert checks["passed"]
    assert set(detail.journal_id) == {"CASH-1", "ACCRUAL-1"}
    ar = history[history.account.eq("1100_AR")].set_index("month")
    assert ar.loc["2026-02", "closing_balance"] == 100
    assert ar.loc["2026-03", "opening_balance"] == 100
    assert ar.loc["2026-03", "closing_balance"] == 65
    assert history[history.account.eq("2100_AP")].iloc[-1].closing_balance == -20
    pd.testing.assert_frame_equal(journal, before)


def test_nonfinite_and_missing_source_identity_fail_closed():
    journal = source()
    journal.loc[0, "debit"] = float("nan")
    with pytest.raises(ValueError, match="Non-finite"):
        build_working_capital_lineage(journal, "2026-03")
    journal = source()
    journal.loc[0, "journal_id"] = None
    with pytest.raises(ValueError, match="identity"):
        build_working_capital_lineage(journal, "2026-03")


def test_empty_account_population_is_valid():
    journal = source().assign(account="1000_CASH")
    detail, history, checks = build_working_capital_lineage(journal, "2026-03")
    assert detail.empty and history.empty and checks["passed"]
