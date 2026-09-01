from __future__ import annotations

from collections import defaultdict

import pandas as pd


TRANSLATION_RESERVE = "3300_FX_TRANSLATION_RESERVE"


def _money(value: float) -> float:
    return round(float(value), 2)


def entity_currency_map(config: dict) -> dict[str, str]:
    return {str(row["code"]): str(row["currency"]) for row in config.get("entities", [])}


def _fx_lookup(macro: pd.DataFrame) -> dict[tuple[str, str], float]:
    if macro.empty:
        return {}
    currencies = [c for c in ["EUR", "USD", "JPY", "CNY", "CZK"] if c in macro.columns]
    lookup: dict[tuple[str, str], float] = {}
    for row in macro.itertuples(index=False):
        month = str(row.month)
        for currency in currencies:
            value = float(getattr(row, currency))
            if value > 0:
                lookup[(month, currency)] = value
    return lookup


def _balance_local_journal_groups(frame: pd.DataFrame) -> pd.DataFrame:
    """Resolve local-currency rounding within each balanced journal.

    EUR journals are already balanced to cents. Dividing individual lines by FX and
    rounding them to local-currency cents can create a small local imbalance. The
    difference is assigned to the largest line on the opposite side of the same
    journal. It is explicitly retained as a rounding adjustment; no P&L or equity
    plug is created.
    """
    out = frame.copy()
    out["local_rounding_adjustment"] = 0.0
    groups = out.groupby(["journal_id", "entity", "functional_currency"], sort=False).groups
    for _, index in groups.items():
        idx = list(index)
        local_debit = _money(out.loc[idx, "local_debit"].sum())
        local_credit = _money(out.loc[idx, "local_credit"].sum())
        diff = _money(local_debit - local_credit)
        if abs(diff) < 0.005:
            continue
        if diff > 0:
            candidates = out.loc[idx][out.loc[idx, "local_credit"].gt(0)]
            target = candidates.local_credit.idxmax() if not candidates.empty else idx[0]
            out.at[target, "local_credit"] = _money(float(out.at[target, "local_credit"]) + diff)
            out.at[target, "local_rounding_adjustment"] = _money(float(out.at[target, "local_rounding_adjustment"]) + diff)
        else:
            adjustment = -diff
            candidates = out.loc[idx][out.loc[idx, "local_debit"].gt(0)]
            target = candidates.local_debit.idxmax() if not candidates.empty else idx[0]
            out.at[target, "local_debit"] = _money(float(out.at[target, "local_debit"]) + adjustment)
            out.at[target, "local_rounding_adjustment"] = _money(float(out.at[target, "local_rounding_adjustment"]) + adjustment)
    return out


def enrich_journal_with_functional_currency(journal: pd.DataFrame, macro: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Add functional-currency amounts to the EUR reporting ledger.

    Macro currency columns represent EUR value of one unit of functional currency.
    Example: USD=0.92 means USD 1 = EUR 0.92. The existing reporting ledger is
    converted to local currency as EUR amount / FX-to-EUR. Local journals are then
    balanced after line-level currency rounding.
    """
    if journal.empty:
        return journal.copy()
    currencies = entity_currency_map(config)
    fx = _fx_lookup(macro)
    out = journal.copy()
    out["functional_currency"] = out.entity.astype(str).map(currencies).fillna("EUR")
    out["fx_to_eur"] = [
        float(fx.get((str(month), str(currency)), 1.0 if str(currency) == "EUR" else 0.0))
        for month, currency in zip(out.month, out.functional_currency)
    ]
    if (out.fx_to_eur <= 0).any():
        missing = out.loc[out.fx_to_eur.le(0), ["month", "entity", "functional_currency"]].drop_duplicates()
        raise ValueError(f"Missing FX rates for functional-currency journal rows: {missing.to_dict(orient='records')}")
    out["local_debit"] = (out.debit.astype(float) / out.fx_to_eur).round(2)
    out["local_credit"] = (out.credit.astype(float) / out.fx_to_eur).round(2)
    out = _balance_local_journal_groups(out)
    out["reporting_debit_from_local"] = (out.local_debit * out.fx_to_eur).round(2)
    out["reporting_credit_from_local"] = (out.local_credit * out.fx_to_eur).round(2)
    return out


def local_trial_balance(local_journal: pd.DataFrame) -> pd.DataFrame:
    if local_journal.empty:
        return pd.DataFrame()
    scope = local_journal.copy()
    scope["local_signed"] = scope.local_debit.astype(float) - scope.local_credit.astype(float)
    monthly = scope.groupby(
        ["month", "entity", "functional_currency", "account"], as_index=False
    ).local_signed.sum()
    months = sorted(scope.month.astype(str).unique())
    keys = scope[["entity", "functional_currency", "account"]].drop_duplicates()
    cumulative: dict[tuple[str, str], float] = defaultdict(float)
    rows: list[dict] = []
    for month in months:
        current = monthly[monthly.month.eq(month)]
        for row in current.itertuples(index=False):
            cumulative[(str(row.entity), str(row.account))] = _money(
                cumulative[(str(row.entity), str(row.account))] + float(row.local_signed)
            )
        for entity, currency, account in keys.itertuples(index=False, name=None):
            rows.append({
                "month": month,
                "entity": str(entity),
                "functional_currency": str(currency),
                "account": str(account),
                "local_balance": _money(cumulative[(str(entity), str(account))]),
            })
    return pd.DataFrame(rows)


def _account_types(chart: pd.DataFrame) -> dict[str, tuple[str, str]]:
    return {
        str(row.account): (str(row.statement), str(row.account_type))
        for row in chart.itertuples(index=False)
    }


def _translated_equity_history(local_journal: pd.DataFrame, chart: pd.DataFrame) -> dict[tuple[str, str, str], float]:
    """Accumulate equity movements in EUR at the rate when each movement arose.

    Share capital therefore remains at its historical issue rate. Retained earnings
    accumulate the translated monthly profit transfers instead of being retranslated
    wholesale at each closing rate.
    """
    meta = _account_types(chart)
    equity_accounts = {account for account, (_, account_type) in meta.items() if account_type == "Equity"}
    if not equity_accounts:
        return {}
    scope = local_journal[local_journal.account.astype(str).isin(equity_accounts)].copy()
    if scope.empty:
        return {}
    scope["translated_signed_flow"] = (
        (scope.local_debit.astype(float) - scope.local_credit.astype(float)) * scope.fx_to_eur.astype(float)
    ).round(2)
    monthly = scope.groupby(["month", "entity", "account"], as_index=False).translated_signed_flow.sum()
    months = sorted(local_journal.month.astype(str).unique())
    entities = sorted(local_journal.entity.astype(str).unique())
    cumulative: dict[tuple[str, str], float] = defaultdict(float)
    result: dict[tuple[str, str, str], float] = {}
    for month in months:
        current = monthly[monthly.month.eq(month)]
        for row in current.itertuples(index=False):
            key = (str(row.entity), str(row.account))
            cumulative[key] = _money(cumulative[key] + float(row.translated_signed_flow))
        for entity in entities:
            for account in equity_accounts:
                result[(month, entity, account)] = _money(cumulative[(entity, account)])
    return result


def build_translation_schedule(
    local_journal: pd.DataFrame,
    macro: pd.DataFrame,
    config: dict,
    chart: pd.DataFrame,
) -> pd.DataFrame:
    """Translate functional-currency legal balances to EUR with explicit CTA.

    Assets and liabilities are translated at closing FX. Equity movements are kept
    at historical transaction/monthly rates: opening share capital stays at its
    historical rate and retained earnings accumulate monthly translated profit.
    The remaining difference is the Currency Translation Adjustment in OCI.
    """
    if local_journal.empty:
        return pd.DataFrame()
    tb = local_trial_balance(local_journal)
    if tb.empty:
        return pd.DataFrame()
    fx = _fx_lookup(macro)
    account_meta = _account_types(chart)
    currencies = entity_currency_map(config)
    equity_history = _translated_equity_history(local_journal, chart)
    first_month = min(local_journal.month.astype(str))
    rows: list[dict] = []

    for (month, entity), grp in tb.groupby(["month", "entity"], sort=True):
        currency = currencies.get(str(entity), "EUR")
        closing_rate = float(fx.get((str(month), currency), 1.0))
        historical_rate = float(fx.get((first_month, currency), closing_rate))
        assets = liabilities = 0.0

        for r in grp.itertuples(index=False):
            account = str(r.account)
            local_balance = float(r.local_balance)
            statement, account_type = account_meta.get(account, ("Balance Sheet", "Other"))
            if statement == "P&L" or account_type == "Equity":
                continue
            translated_signed = _money(local_balance * closing_rate)
            if account_type in {"Asset", "Contra Asset"}:
                assets = _money(assets + translated_signed)
            elif account_type == "Liability":
                liabilities = _money(liabilities - translated_signed)

        translated_share_capital = _money(-equity_history.get((str(month), str(entity), "3000_SHARE_CAPITAL"), 0.0))
        translated_retained_earnings = _money(-equity_history.get((str(month), str(entity), "3200_RETAINED_EARNINGS"), 0.0))
        translated_other_equity = 0.0
        for account, (_, account_type) in account_meta.items():
            if account_type != "Equity" or account in {"3000_SHARE_CAPITAL", "3200_RETAINED_EARNINGS", TRANSLATION_RESERVE}:
                continue
            translated_other_equity = _money(
                translated_other_equity - equity_history.get((str(month), str(entity), account), 0.0)
            )
        equity_before_cta = _money(translated_share_capital + translated_retained_earnings + translated_other_equity)
        cta = _money(assets - liabilities - equity_before_cta)

        local_re = float(grp.loc[grp.account.astype(str).eq("3200_RETAINED_EARNINGS"), "local_balance"].sum())
        re_effective_rate = (
            translated_retained_earnings / (-local_re)
            if abs(local_re) > 0.005 else closing_rate
        )
        rows.append({
            "month": str(month),
            "entity": str(entity),
            "functional_currency": currency,
            "closing_fx_to_eur": closing_rate,
            "historical_equity_fx_to_eur": historical_rate,
            "retained_earnings_effective_fx_to_eur": re_effective_rate,
            "translated_assets": assets,
            "translated_liabilities": liabilities,
            "translated_share_capital": translated_share_capital,
            "translated_retained_earnings": translated_retained_earnings,
            "translated_other_equity": translated_other_equity,
            "translated_equity_before_cta": equity_before_cta,
            "fx_translation_reserve": cta,
            "translated_equity": _money(equity_before_cta + cta),
            "translation_balance_check": _money(assets - liabilities - equity_before_cta - cta),
        })
    return pd.DataFrame(rows)


def constant_currency_analysis(
    management: pd.DataFrame,
    macro: pd.DataFrame,
    config: dict,
    end_month: str,
) -> pd.DataFrame:
    """Show reported versus prior-year-rate revenue and EBIT for foreign entities."""
    if management.empty:
        return pd.DataFrame()
    currencies = entity_currency_map(config)
    fx = _fx_lookup(macro)
    current = pd.Period(end_month, freq="M")
    prior = current - 12
    scope = management[management.month.eq(str(current))].groupby(["entity", "division"], as_index=False).agg(
        revenue=("revenue", "sum"), ebit=("ebit", "sum")
    )
    rows: list[dict] = []
    for r in scope.itertuples(index=False):
        entity = str(r.entity)
        currency = currencies.get(entity, "EUR")
        current_rate = float(fx.get((str(current), currency), 1.0))
        prior_rate = float(fx.get((str(prior), currency), current_rate))
        revenue_local = float(r.revenue) / current_rate if current_rate else 0.0
        ebit_local = float(r.ebit) / current_rate if current_rate else 0.0
        cc_revenue = _money(revenue_local * prior_rate)
        cc_ebit = _money(ebit_local * prior_rate)
        rows.append({
            "month": str(current), "entity": entity, "division": str(r.division),
            "functional_currency": currency,
            "current_fx_to_eur": current_rate, "constant_currency_fx_to_eur": prior_rate,
            "reported_revenue": _money(r.revenue), "constant_currency_revenue": cc_revenue,
            "revenue_fx_effect": _money(float(r.revenue) - cc_revenue),
            "reported_ebit": _money(r.ebit), "constant_currency_ebit": cc_ebit,
            "ebit_fx_effect": _money(float(r.ebit) - cc_ebit),
        })
    return pd.DataFrame(rows)


def validate_fx_translation(local_journal: pd.DataFrame, translation: pd.DataFrame) -> dict:
    if local_journal.empty or translation.empty:
        return {
            "functional_currency_journal_max_gap": 0.0,
            "fx_roundtrip_max_gap": 0.0,
            "fx_translation_balance_max_gap": 0.0,
            "fx_local_rounding_adjustment_eur_max": 0.0,
            "passed": False,
        }
    by_journal = local_journal.groupby(["journal_id", "entity", "functional_currency"], as_index=False).agg(
        debit=("local_debit", "sum"), credit=("local_credit", "sum")
    )
    local_gap = float((by_journal.debit - by_journal.credit).abs().max()) if not by_journal.empty else 0.0

    reconstructed = local_journal.groupby(["journal_id", "entity"], as_index=False).agg(
        original_debit=("debit", "sum"), original_credit=("credit", "sum"),
        reconstructed_debit=("reporting_debit_from_local", "sum"),
        reconstructed_credit=("reporting_credit_from_local", "sum"),
    )
    debit_gap = (reconstructed.original_debit - reconstructed.reconstructed_debit).abs()
    credit_gap = (reconstructed.original_credit - reconstructed.reconstructed_credit).abs()
    roundtrip = float(max(debit_gap.max(), credit_gap.max())) if not reconstructed.empty else 0.0

    adjustment_eur = (local_journal.local_rounding_adjustment.abs() * local_journal.fx_to_eur).astype(float)
    adjustment_eur_max = float(adjustment_eur.max()) if len(adjustment_eur) else 0.0
    translation_gap = float(translation.translation_balance_check.abs().max())
    return {
        "functional_currency_journal_max_gap": round(local_gap, 2),
        "fx_roundtrip_max_gap": round(roundtrip, 2),
        "fx_translation_balance_max_gap": round(translation_gap, 2),
        "fx_local_rounding_adjustment_eur_max": round(adjustment_eur_max, 2),
        "passed": local_gap <= 0.01 and roundtrip <= 0.10 and translation_gap <= 0.01 and adjustment_eur_max <= 0.10,
    }
