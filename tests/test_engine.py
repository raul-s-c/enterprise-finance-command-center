from enterprise_finance.engine import load_config, month_range, macro_series, operational_model, build_journal, validate


def test_journal_balances():
    config = load_config()
    months = month_range("2026-08", 6)
    macro = macro_series(months, config["group"]["seed"])
    operational = operational_model(config, months, macro)
    journal = build_journal(config, operational)
    assert validate(journal)["passed"]


def test_deterministic_operational_model():
    config = load_config()
    months = month_range("2026-08", 6)
    macro = macro_series(months, config["group"]["seed"])
    a = operational_model(config, months, macro)
    b = operational_model(config, months, macro)
    assert a.equals(b)
