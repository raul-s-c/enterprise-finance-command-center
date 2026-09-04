from __future__ import annotations

import hashlib
import math

import pandas as pd


FX_CURRENCIES = ("EUR", "USD", "JPY", "CNY", "CZK")
SOURCE_ACCOUNTS = {"1100_AR": "Receivable", "2100_AP": "Payable", "1150_IC_AR": "Receivable", "2150_IC_AP": "Payable"}


def _money(value: float) -> float:
    return round(float(value), 2)


def _bucket(value: str, modulo: int = 100) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:12], 16) % modulo


def _entity_currencies(config: dict) -> dict[str, str]:
    return {str(row["code"]): str(row["currency"]) for row in config.get("entities", [])}


def _rates(macro: pd.DataFrame) -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = {}
    for row in macro.itertuples(index=False):
        for currency in FX_CURRENCIES:
            if hasattr(row, currency):
                out[(str(row.month), currency)] = float(getattr(row, currency))
    return out


def _contract_currency(row: pd.Series, functional: str, entity_currency: dict[str, str]) -> str | None:
    key = f"{row.journal_id}|{row.account}|{row.entity}"
    if str(row.account) in {"1150_IC_AR", "2150_IC_AP"}:
        seller = str(row.entity) if str(row.account) == "1150_IC_AR" else str(row.counterparty)
        candidate = entity_currency[seller]
        return candidate if candidate != functional else None
    if str(row.counterparty) in entity_currency:
        candidate = entity_currency[str(row.counterparty)]
        return candidate if candidate != functional else None
    if _bucket(key) >= 18:
        return None
    choices = [currency for currency in FX_CURRENCIES if currency != functional]
    return choices[_bucket(key + "|currency", len(choices))]


def _contract_id(row: pd.Series) -> str:
    seller, buyer = (str(row.entity), str(row.counterparty))
    if str(row.account) == "2150_IC_AP":
        seller, buyer = buyer, seller
    return f"IC-{row.month}-{seller}-{buyer}-{row.division}"


def build_intercompany_contracts(journal: pd.DataFrame, macro: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Reconcile both legal source legs before assigning one synthetic contract policy."""
    source = journal[
        journal.account.isin(["1150_IC_AR", "2150_IC_AP"])
        & journal.journal_type.isin(["intercompany_sale", "intercompany_purchase"])
    ].copy()
    columns = ["contract_id", "issue_month", "seller", "buyer", "division", "transaction_currency",
               "transaction_amount", "original_reporting_eur", "receivable_journal_id",
               "payable_journal_id", "payment_terms_months", "settlement_month"]
    if source.empty:
        return pd.DataFrame(columns=columns)
    source["contract_id"] = source.apply(_contract_id, axis=1)
    currencies, rates = _entity_currencies(config), _rates(macro)
    records = []
    for contract_id, group in source.groupby("contract_id", sort=True):
        ar, ap = group[group.account.eq("1150_IC_AR")], group[group.account.eq("2150_IC_AP")]
        if len(ar) != 1 or len(ap) != 1:
            raise ValueError(f"Intercompany contract requires exactly two reciprocal source legs: {contract_id}")
        receivable, payable = ar.iloc[0], ap.iloc[0]
        ar_value = float(receivable.debit) - float(receivable.credit)
        ap_value = float(payable.credit) - float(payable.debit)
        if not all(math.isfinite(v) and v > 0 for v in [ar_value, ap_value]) or abs(ar_value-ap_value) > 0.02:
            raise ValueError(f"Intercompany contract source amounts do not reconcile: {contract_id}")
        currency = currencies[str(receivable.entity)]
        rate = rates[(str(receivable.month), currency)]
        if not math.isfinite(rate) or rate <= 0:
            raise ValueError(f"Invalid contract FX rate: {contract_id}")
        terms = 1 + _bucket(contract_id + "|terms", 2)
        records.append(dict(zip(columns, [contract_id, str(receivable.month), str(receivable.entity),
            str(payable.entity), str(receivable.division), currency, round(ar_value/rate, 4),
            _money(ar_value), str(receivable.journal_id), str(payable.journal_id), terms,
            str(pd.Period(str(receivable.month), freq="M") + terms)])))
    return pd.DataFrame(records, columns=columns)


def build_transaction_documents(journal: pd.DataFrame, macro: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Create deterministic foreign-currency documents from actual AR/AP source journals."""
    columns = [
        "document_id", "issue_month", "settlement_month", "entity", "division", "counterparty",
        "document_type", "source_account", "functional_currency", "transaction_currency",
        "original_reporting_eur", "transaction_amount", "issue_transaction_fx_to_eur",
        "issue_functional_fx_to_eur", "original_functional_amount", "payment_terms_months",
        "source_journal_id", "contract_id",
    ]
    if journal.empty or macro.empty:
        return pd.DataFrame(columns=columns)
    entity_currency = _entity_currencies(config)
    rates = _rates(macro)
    source = journal[journal.account.astype(str).isin(SOURCE_ACCOUNTS)].copy()
    source = source[~source.journal_type.astype(str).isin(["collection", "supplier_payment", "intercompany_settlement", "closing"])]
    source = source.groupby(
        ["month", "entity", "division", "journal_id", "journal_type", "account", "counterparty"],
        as_index=False,
        dropna=False,
    ).agg(debit=("debit", "sum"), credit=("credit", "sum"))
    rows: list[dict] = []
    for _, row in source.iterrows():
        functional = entity_currency.get(str(row.entity), "EUR")
        transaction = _contract_currency(row, functional, entity_currency)
        if not transaction:
            continue
        original = abs(float(row.debit) - float(row.credit))
        issue_month = str(row.month)
        transaction_rate = float(rates.get((issue_month, transaction), 0.0))
        functional_rate = float(rates.get((issue_month, functional), 0.0))
        if original <= 0 or transaction_rate <= 0 or functional_rate <= 0:
            continue
        document_id = f"FX-{row.journal_id}-{row.account}"
        contract_id = _contract_id(row) if str(row.account) in {"1150_IC_AR", "2150_IC_AP"} else document_id
        terms = 1 + _bucket(contract_id + "|terms", 2)
        settlement = str(pd.Period(issue_month, freq="M") + terms)
        transaction_amount = original / transaction_rate
        rows.append({
            "document_id": document_id,
            "source_journal_id": str(row.journal_id),
            "contract_id": contract_id,
            "issue_month": issue_month,
            "settlement_month": settlement,
            "entity": str(row.entity),
            "division": str(row.division),
            "counterparty": str(row.counterparty),
            "document_type": SOURCE_ACCOUNTS[str(row.account)],
            "source_account": str(row.account),
            "functional_currency": functional,
            "transaction_currency": transaction,
            "original_reporting_eur": _money(original),
            "transaction_amount": round(transaction_amount, 4),
            "issue_transaction_fx_to_eur": transaction_rate,
            "issue_functional_fx_to_eur": functional_rate,
            "original_functional_amount": _money(original / functional_rate),
            "payment_terms_months": terms,
        })
    return pd.DataFrame(rows, columns=columns).sort_values("document_id").reset_index(drop=True)


def build_transaction_fx_snapshots(
    documents: pd.DataFrame, macro: pd.DataFrame, end_month: str
) -> pd.DataFrame:
    """Remeasure open documents monthly and separate realized from unrealized FX."""
    columns = [
        "snapshot_month", "document_id", "entity", "division", "counterparty", "document_type",
        "functional_currency", "transaction_currency", "status", "age_months", "transaction_amount",
        "transaction_fx_to_eur", "functional_fx_to_eur", "carrying_reporting_eur",
        "carrying_functional_amount", "unrealized_fx_gain_loss_functional",
        "realized_fx_gain_loss_functional", "monthly_fx_gain_loss_functional",
        "cumulative_fx_gain_loss_functional", "unrealized_fx_gain_loss_eur",
        "realized_fx_gain_loss_eur", "monthly_fx_gain_loss_eur", "cumulative_fx_gain_loss_eur",
    ]
    if documents.empty:
        return pd.DataFrame(columns=columns)
    rates = _rates(macro)
    final = pd.Period(end_month, freq="M")
    rows: list[dict] = []
    for doc in documents.itertuples(index=False):
        issue = pd.Period(str(doc.issue_month), freq="M")
        settlement = pd.Period(str(doc.settlement_month), freq="M")
        last = min(settlement, final)
        previous_functional = float(doc.original_functional_amount)
        cumulative_functional = cumulative_eur = 0.0
        for period in pd.period_range(issue, last, freq="M"):
            month = str(period)
            transaction_rate = float(rates[(month, str(doc.transaction_currency))])
            functional_rate = float(rates[(month, str(doc.functional_currency))])
            carrying = _money(float(doc.transaction_amount) * transaction_rate)
            carrying_functional = _money(carrying / functional_rate)
            sign = 1.0 if str(doc.document_type) == "Receivable" else -1.0
            movement_functional = _money(sign * (carrying_functional - previous_functional))
            movement_eur = _money(movement_functional * functional_rate)
            cumulative_functional = _money(cumulative_functional + movement_functional)
            cumulative_eur = _money(cumulative_eur + movement_eur)
            settled = period == settlement and settlement <= final
            rows.append({
                "snapshot_month": month,
                "document_id": str(doc.document_id),
                "entity": str(doc.entity),
                "division": str(doc.division),
                "counterparty": str(doc.counterparty),
                "document_type": str(doc.document_type),
                "functional_currency": str(doc.functional_currency),
                "transaction_currency": str(doc.transaction_currency),
                "status": "Settled" if settled else "Open",
                "age_months": int(period.ordinal - issue.ordinal),
                "transaction_amount": float(doc.transaction_amount),
                "transaction_fx_to_eur": transaction_rate,
                "functional_fx_to_eur": functional_rate,
                "carrying_reporting_eur": carrying,
                "carrying_functional_amount": carrying_functional,
                "unrealized_fx_gain_loss_functional": 0.0 if settled else movement_functional,
                "realized_fx_gain_loss_functional": movement_functional if settled else 0.0,
                "monthly_fx_gain_loss_functional": movement_functional,
                "cumulative_fx_gain_loss_functional": cumulative_functional,
                "unrealized_fx_gain_loss_eur": 0.0 if settled else movement_eur,
                "realized_fx_gain_loss_eur": movement_eur if settled else 0.0,
                "monthly_fx_gain_loss_eur": movement_eur,
                "cumulative_fx_gain_loss_eur": cumulative_eur,
            })
            previous_functional = carrying_functional
    return pd.DataFrame(rows, columns=columns)


def summarize_transaction_fx(snapshots: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "month", "entity", "transaction_currency", "open_documents", "gross_receivable_eur",
        "gross_payable_eur", "net_exposure_eur", "unrealized_fx_gain_loss_eur",
        "realized_fx_gain_loss_eur", "total_fx_gain_loss_eur",
    ]
    if snapshots.empty:
        return pd.DataFrame(columns=columns)
    current = snapshots.copy()
    current["gross_receivable_eur"] = current.carrying_reporting_eur.where(
        current.document_type.eq("Receivable") & current.status.eq("Open"), 0.0
    )
    current["gross_payable_eur"] = current.carrying_reporting_eur.where(
        current.document_type.eq("Payable") & current.status.eq("Open"), 0.0
    )
    current["open_document"] = current.status.eq("Open").astype(int)
    out = current.groupby(["snapshot_month", "entity", "transaction_currency"], as_index=False).agg(
        open_documents=("open_document", "sum"),
        gross_receivable_eur=("gross_receivable_eur", "sum"),
        gross_payable_eur=("gross_payable_eur", "sum"),
        unrealized_fx_gain_loss_eur=("unrealized_fx_gain_loss_eur", "sum"),
        realized_fx_gain_loss_eur=("realized_fx_gain_loss_eur", "sum"),
        total_fx_gain_loss_eur=("monthly_fx_gain_loss_eur", "sum"),
    ).rename(columns={"snapshot_month": "month"})
    out["net_exposure_eur"] = out.gross_receivable_eur - out.gross_payable_eur
    money = [column for column in columns if column.endswith("_eur")]
    out[money] = out[money].round(2)
    return out[columns]


def _validate_transaction_fx_identities(
    documents: pd.DataFrame, snapshots: pd.DataFrame, summary: pd.DataFrame, macro: pd.DataFrame
) -> dict:
    document_duplicates = int(documents.document_id.duplicated().sum()) if not documents.empty else 1
    same_currency = int(documents.functional_currency.eq(documents.transaction_currency).sum()) if not documents.empty else 1
    snapshot_duplicates = int(snapshots.duplicated(["snapshot_month", "document_id"]).sum()) if not snapshots.empty else 1
    rate_lookup = _rates(macro)
    carrying_gap = 0.0
    lifecycle_gap = 0.0
    if not snapshots.empty:
        expected = snapshots.apply(
            lambda row: float(row.transaction_amount) * rate_lookup[(str(row.snapshot_month), str(row.transaction_currency))],
            axis=1,
        )
        carrying_gap = float((snapshots.carrying_reporting_eur - expected).abs().max())
        final = snapshots.sort_values(["document_id", "snapshot_month"]).groupby("document_id").tail(1)
        direction = final.document_type.map({"Receivable": 1.0, "Payable": -1.0}).astype(float)
        original_functional = documents.set_index("document_id").original_functional_amount
        expected_cumulative = direction * (
            final.carrying_functional_amount.astype(float)
            - final.document_id.map(original_functional).astype(float)
        )
        lifecycle_gap = float((final.cumulative_fx_gain_loss_functional - expected_cumulative).abs().max())
    summary_gap = 1.0
    if not summary.empty:
        summary_gap = float((summary.total_fx_gain_loss_eur - summary.unrealized_fx_gain_loss_eur - summary.realized_fx_gain_loss_eur).abs().max())
    checks = {
        "transaction_fx_document_duplicate_rows": document_duplicates,
        "transaction_fx_same_functional_currency_rows": same_currency,
        "transaction_fx_snapshot_duplicate_rows": snapshot_duplicates,
        "transaction_fx_carrying_value_max_gap": round(carrying_gap, 2),
        "transaction_fx_lifecycle_pnl_max_gap": round(lifecycle_gap, 2),
        "transaction_fx_summary_pnl_max_gap": round(summary_gap, 2),
    }
    checks["passed"] = bool(
        document_duplicates == 0 and same_currency == 0 and snapshot_duplicates == 0
        and carrying_gap <= 0.02 and lifecycle_gap <= 0.02 and summary_gap <= 0.02
    )
    return checks


def _frame_difference(actual: pd.DataFrame, expected: pd.DataFrame, keys: list[str]) -> tuple[int, float]:
    """Compare key coverage, metadata and every measure, not only internal arithmetic."""
    if not set(expected.columns).issubset(actual.columns):
        return 1, 0.0
    if actual.duplicated(keys).any() or expected.duplicated(keys).any():
        return 1, 0.0
    merged = expected.merge(actual[expected.columns], on=keys, how="outer", suffixes=("_expected", "_actual"), indicator=True)
    errors = int(merged._merge.ne("both").sum())
    matched = merged[merged._merge.eq("both")]
    max_gap = 0.0
    for column in expected.columns:
        if column in keys:
            continue
        left, right = matched[column + "_expected"], matched[column + "_actual"]
        if pd.api.types.is_numeric_dtype(expected[column]):
            values = pd.to_numeric(right, errors="coerce")
            finite = values.map(lambda value: pd.notna(value) and math.isfinite(float(value)))
            errors += int((~finite).sum())
            gap = (left[finite].astype(float) - values[finite].astype(float)).abs().max()
            if pd.notna(gap):
                max_gap = max(max_gap, float(gap))
        else:
            errors += int(left.fillna("").astype(str).ne(right.fillna("").astype(str)).sum())
    return errors, max_gap


def validate_transaction_fx(
    documents: pd.DataFrame, snapshots: pd.DataFrame, summary: pd.DataFrame, macro: pd.DataFrame,
    *, end_month: str | None = None, journal: pd.DataFrame | None = None,
    config: dict | None = None, contracts: pd.DataFrame | None = None,
) -> dict:
    """Retain v0.20 identities and add source, lifecycle and detail-to-summary tie-outs."""
    checks = {"transaction_fx_integrity_errors": 0}
    try:
        if any(frame.empty for frame in [documents, snapshots, summary, macro]):
            raise ValueError("Missing FX dataset")
        if documents.document_id.duplicated().any() or snapshots.duplicated(["snapshot_month", "document_id"]).any():
            raise ValueError("Duplicate document or snapshot")
        for frame in [documents, snapshots, summary, macro]:
            numeric = frame.select_dtypes(include="number")
            if not numeric.map(lambda value: pd.notna(value) and math.isfinite(float(value))).all().all():
                raise ValueError("Non-finite FX measure")
        checks.update(_validate_transaction_fx_identities(documents, snapshots, summary, macro))
        close_month = end_month or str(snapshots.snapshot_month.max())
        expected_snapshots = build_transaction_fx_snapshots(documents, macro, close_month)
        errors, gap = _frame_difference(snapshots, expected_snapshots, ["snapshot_month", "document_id"])
        comparisons_passed = errors == 0 and gap <= 0.02
        checks["transaction_fx_snapshot_integrity_errors"] = errors
        checks["transaction_fx_snapshot_source_max_gap"] = round(gap, 6)
        errors, gap = _frame_difference(summary, summarize_transaction_fx(snapshots), ["month", "entity", "transaction_currency"])
        comparisons_passed = comparisons_passed and errors == 0 and gap <= 0.02
        checks["transaction_fx_summary_integrity_errors"] = errors
        checks["transaction_fx_summary_source_max_gap"] = round(gap, 6)
        if journal is not None:
            if config is None or contracts is None:
                raise ValueError("Source validation requires config and contract register")
            expected_contracts = build_intercompany_contracts(journal, macro, config)
            errors, gap = _frame_difference(contracts, expected_contracts, ["contract_id"])
            comparisons_passed = comparisons_passed and errors == 0 and gap <= 0.02
            checks["transaction_fx_contract_integrity_errors"] = errors
            checks["transaction_fx_contract_source_max_gap"] = round(gap, 6)
            errors, gap = _frame_difference(documents, build_transaction_documents(journal, macro, config), ["document_id"])
            comparisons_passed = comparisons_passed and errors == 0 and gap <= 0.02
            checks["transaction_fx_document_source_errors"] = errors
            checks["transaction_fx_document_source_max_gap"] = round(gap, 6)
        checks["passed"] = bool(checks.get("passed", False) and comparisons_passed and all(
            value <= (0.02 if key.endswith("max_gap") else 0)
            for key, value in checks.items()
            if key != "passed" and (key.endswith("errors") or key.endswith("source_max_gap"))
        ))
    except (KeyError, ValueError, TypeError, IndexError, ZeroDivisionError):
        checks["transaction_fx_integrity_errors"] += 1
        checks["passed"] = False
    return checks
