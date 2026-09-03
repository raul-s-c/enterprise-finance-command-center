from __future__ import annotations

import re

import pandas as pd


ACTIVE_STATUSES = {"Open", "In Progress"}
VALID_STATUSES = ACTIVE_STATUSES | {"Closed", "Cancelled"}

ACTION_COLUMNS = [
    "action_id",
    "action_key",
    "review_id",
    "origin_review_id",
    "review_month",
    "scope_level",
    "entity",
    "division",
    "priority",
    "owner_role",
    "opened_month",
    "last_seen_month",
    "due_month",
    "closed_month",
    "cancelled_month",
    "status",
    "age_months",
    "carry_forward_months",
    "overdue_months",
    "overdue",
    "escalation_level",
    "occurrence_count",
    "action",
    "expected_outcome",
    "closure_evidence",
    "trigger_metric",
    "trigger_value",
    "source_dataset",
]

HISTORY_COLUMNS = ["snapshot_month", *ACTION_COLUMNS]
CHANGE_COLUMNS = [
    "change_id",
    "action_id",
    "change_month",
    "change_type",
    "field_name",
    "previous_value",
    "new_value",
    "evidence",
]


def _slug(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", str(value).upper()).strip("-")


def _period_distance(start: object, end: str) -> int:
    try:
        start_period = pd.Period(str(start), freq="M")
        end_period = pd.Period(end, freq="M")
        return max((end_period.year - start_period.year) * 12 + end_period.month - start_period.month, 0)
    except (TypeError, ValueError):
        return 0


def _text(value: object) -> str:
    return "" if pd.isna(value) else str(value)


def _status(value: object) -> str:
    normalized = _text(value).strip().lower()
    return {
        "open": "Open",
        "in progress": "In Progress",
        "closed": "Closed",
        "cancelled": "Cancelled",
        "canceled": "Cancelled",
    }.get(normalized, _text(value).strip())


def action_key(row: pd.Series | dict) -> str:
    get = row.get
    return "|".join(
        _slug(get(field, ""))
        for field in ["scope_level", "entity", "division", "trigger_metric", "source_dataset"]
    )


def _empty(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _upgrade_previous(previous: pd.DataFrame | None) -> pd.DataFrame:
    if previous is None or previous.empty:
        return _empty(ACTION_COLUMNS)
    upgraded = previous.copy()
    if "status" not in upgraded:
        upgraded["status"] = "Open"
    upgraded["status"] = upgraded["status"].map(_status)
    defaults: dict[str, object] = {
        "action_key": "",
        "origin_review_id": "",
        "opened_month": "",
        "last_seen_month": "",
        "closed_month": "",
        "cancelled_month": "",
        "age_months": 0,
        "carry_forward_months": 0,
        "overdue_months": 0,
        "overdue": False,
        "escalation_level": "None",
        "occurrence_count": 1,
        "closure_evidence": "",
    }
    for column, default in defaults.items():
        if column not in upgraded:
            upgraded[column] = default
    upgraded["action_key"] = upgraded.apply(
        lambda row: _text(row.action_key) or action_key(row), axis=1
    )
    upgraded["origin_review_id"] = upgraded.apply(
        lambda row: _text(row.origin_review_id) or _text(row.review_id), axis=1
    )
    upgraded["opened_month"] = upgraded.apply(
        lambda row: _text(row.opened_month) or _text(row.review_month), axis=1
    )
    upgraded["last_seen_month"] = upgraded.apply(
        lambda row: _text(row.last_seen_month) or _text(row.review_month), axis=1
    )
    for column in ACTION_COLUMNS:
        if column not in upgraded:
            upgraded[column] = ""
    return upgraded[ACTION_COLUMNS].copy()


def _escalation(priority: str, overdue_months: int) -> str:
    if overdue_months <= 0:
        return "None"
    if priority == "P1" or overdue_months >= 2:
        return "Executive"
    return "Management"


def _refresh_dates(record: dict, end_month: str) -> dict:
    status = _status(record.get("status", "Open"))
    age = _period_distance(record.get("opened_month"), end_month)
    overdue_months = (
        _period_distance(record.get("due_month"), end_month)
        if status in ACTIVE_STATUSES and str(record.get("due_month", "")) < end_month
        else 0
    )
    record.update(
        {
            "status": status,
            "age_months": age,
            "carry_forward_months": age if status in ACTIVE_STATUSES else 0,
            "overdue_months": overdue_months,
            "overdue": bool(overdue_months > 0),
            "escalation_level": _escalation(_text(record.get("priority")), overdue_months),
        }
    )
    return record


def _change(action_id: str, month: str, kind: str, field: str, before: object, after: object, evidence: str) -> dict:
    return {
        "change_id": "-".join(["CHG", month.replace("-", ""), _slug(action_id), _slug(kind), _slug(field)]),
        "action_id": action_id,
        "change_month": month,
        "change_type": kind,
        "field_name": field,
        "previous_value": _text(before),
        "new_value": _text(after),
        "evidence": evidence,
    }


def build_action_lifecycle(
    new_actions: pd.DataFrame,
    current_review: pd.DataFrame,
    end_month: str,
    previous_actions: pd.DataFrame | None = None,
    action_history: pd.DataFrame | None = None,
    review_history: pd.DataFrame | None = None,
    change_history: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Reconcile current required actions with the persisted register and audit trails."""
    legacy_migration = bool(
        previous_actions is not None and not previous_actions.empty and "action_key" not in previous_actions.columns
    )
    previous = _upgrade_previous(previous_actions)
    incoming = new_actions.copy()
    if not incoming.empty:
        incoming["action_key"] = incoming.apply(action_key, axis=1)

    active_previous = previous[previous.status.isin(ACTIVE_STATUSES)].copy()
    previous_by_key = {row.action_key: row for _, row in active_previous.iterrows()}
    incoming_keys = set(incoming.action_key) if not incoming.empty else set()
    records: list[dict] = []
    changes: list[dict] = []

    if legacy_migration:
        changes.extend(
            _change(
                _text(row.action_id),
                end_month,
                "Migrated",
                "schema_version",
                "0.16",
                "0.17",
                "Backward-compatible migration from the v0.16 action register.",
            )
            for _, row in previous.iterrows()
        )

    if action_history is not None and not action_history.empty and {"snapshot_month", "action_id"} <= set(action_history.columns):
        latest_snapshot = (
            action_history.sort_values("snapshot_month").drop_duplicates("action_id", keep="last").set_index("action_id")
        )
        tracked_fields = ["status", "owner_role", "priority", "due_month", "closure_evidence"]
        for _, row in previous.iterrows():
            if row.action_id not in latest_snapshot.index:
                continue
            snapshot = latest_snapshot.loc[row.action_id]
            for field in tracked_fields:
                before, after = _text(snapshot.get(field, "")), _text(row.get(field, ""))
                if before == after:
                    continue
                changes.append(
                    _change(
                        _text(row.action_id),
                        end_month,
                        "Status Changed" if field == "status" else "Field Changed",
                        field,
                        before,
                        after,
                        _text(row.closure_evidence) or "Persisted register update before the monthly close.",
                    )
                )

    preserved = previous[~previous.status.isin(ACTIVE_STATUSES)]
    records.extend(preserved.to_dict("records"))

    for _, row in active_previous.iterrows():
        if row.action_key in incoming_keys:
            continue
        record = row.to_dict()
        record.update(
            {
                "status": "Closed",
                "closed_month": end_month,
                "closure_evidence": f"Trigger no longer requires action in the reconciled {end_month} performance review.",
            }
        )
        records.append(_refresh_dates(record, end_month))
        changes.append(
            _change(
                _text(row.action_id),
                end_month,
                "Status Changed",
                "status",
                row.status,
                "Closed",
                record["closure_evidence"],
            )
        )

    for _, row in incoming.iterrows():
        prior = previous_by_key.get(row.action_key)
        if prior is None:
            record = row.to_dict()
            base_action_id = _text(row.action_id)
            existing_ids = set(previous.action_id.astype(str)) | {str(item.get("action_id", "")) for item in records}
            if base_action_id in existing_ids:
                cycle = 2
                while f"{base_action_id}-CYCLE-{cycle}" in existing_ids:
                    cycle += 1
                record["action_id"] = f"{base_action_id}-CYCLE-{cycle}"
            record.update(
                {
                    "action_key": row.action_key,
                    "origin_review_id": row.review_id,
                    "opened_month": end_month,
                    "last_seen_month": end_month,
                    "closed_month": "",
                    "cancelled_month": "",
                    "status": "Open",
                    "occurrence_count": 1,
                    "closure_evidence": "",
                }
            )
            changes.append(
                _change(
                    _text(record["action_id"]), end_month, "Created", "status", "", "Open", _text(row.source_dataset)
                )
            )
        else:
            record = prior.to_dict()
            record.update(
                {
                    "review_id": row.review_id,
                    "review_month": end_month,
                    "last_seen_month": end_month,
                    "scope_level": row.scope_level,
                    "entity": row.entity,
                    "division": row.division,
                    "trigger_metric": row.trigger_metric,
                    "trigger_value": row.trigger_value,
                    "source_dataset": row.source_dataset,
                    "expected_outcome": row.expected_outcome,
                    "occurrence_count": int(prior.occurrence_count) + int(_text(prior.last_seen_month) != end_month),
                }
            )
            if _text(prior.last_seen_month) != end_month:
                changes.append(
                    _change(
                        _text(prior.action_id),
                        end_month,
                        "Carried Forward",
                        "last_seen_month",
                        prior.last_seen_month,
                        end_month,
                        _text(row.source_dataset),
                    )
                )
        records.append(_refresh_dates(record, end_month))

    actions = pd.DataFrame(records, columns=ACTION_COLUMNS)
    if not actions.empty:
        status_order = {"Open": 0, "In Progress": 1, "Closed": 2, "Cancelled": 3}
        actions["_status_order"] = actions.status.map(status_order).fillna(9)
        actions = actions.sort_values(
            ["_status_order", "overdue", "priority", "opened_month", "action_id"],
            ascending=[True, False, True, True, True],
        ).drop(columns="_status_order").reset_index(drop=True)

    current_snapshots = actions.copy()
    current_snapshots.insert(0, "snapshot_month", end_month)
    prior_action_history = action_history.copy() if action_history is not None else _empty(HISTORY_COLUMNS)
    for column in HISTORY_COLUMNS:
        if column not in prior_action_history:
            prior_action_history[column] = ""
    snapshots = pd.concat([prior_action_history[HISTORY_COLUMNS], current_snapshots[HISTORY_COLUMNS]], ignore_index=True)
    snapshots = snapshots.drop_duplicates(["snapshot_month", "action_id"], keep="last")

    prior_review_history = review_history.copy() if review_history is not None else _empty(list(current_review.columns))
    reviews = pd.concat([prior_review_history, current_review], ignore_index=True)
    if "review_id" in reviews:
        reviews = reviews.drop_duplicates("review_id", keep="last")

    current_changes = pd.DataFrame(changes, columns=CHANGE_COLUMNS)
    prior_changes = change_history.copy() if change_history is not None else _empty(CHANGE_COLUMNS)
    for column in CHANGE_COLUMNS:
        if column not in prior_changes:
            prior_changes[column] = ""
    change_log = pd.concat([prior_changes[CHANGE_COLUMNS], current_changes], ignore_index=True)
    change_log = change_log.drop_duplicates("change_id", keep="last")

    active = actions[actions.status.isin(ACTIVE_STATUSES)]
    summary = pd.DataFrame(
        [
            {
                "review_month": end_month,
                "total_actions": int(len(actions)),
                "open_actions": int(actions.status.eq("Open").sum()),
                "in_progress_actions": int(actions.status.eq("In Progress").sum()),
                "closed_actions": int(actions.status.eq("Closed").sum()),
                "cancelled_actions": int(actions.status.eq("Cancelled").sum()),
                "overdue_actions": int(active.overdue.sum()) if not active.empty else 0,
                "carry_forward_actions": int(active.carry_forward_months.gt(0).sum()) if not active.empty else 0,
                "p1_active_actions": int((active.priority == "P1").sum()) if not active.empty else 0,
                "executive_escalations": int(active.escalation_level.eq("Executive").sum()) if not active.empty else 0,
                "average_active_age_months": round(float(active.age_months.mean()), 2) if not active.empty else 0.0,
            }
        ]
    )
    return actions, snapshots, reviews, change_log, summary


def validate_action_lifecycle(
    actions: pd.DataFrame,
    action_history: pd.DataFrame,
    review_history: pd.DataFrame,
    change_history: pd.DataFrame,
    current_required_actions: pd.DataFrame,
    summary: pd.DataFrame,
    end_month: str,
) -> dict:
    missing_columns = len(set(ACTION_COLUMNS) - set(actions.columns))
    duplicate_ids = int(actions.action_id.duplicated().sum()) if "action_id" in actions else len(actions)
    active = actions[actions.status.isin(ACTIVE_STATUSES)] if missing_columns == 0 else _empty(ACTION_COLUMNS)
    duplicate_active_keys = int(active.action_key.duplicated().sum()) if not active.empty else 0
    invalid_statuses = int((~actions.status.isin(VALID_STATUSES)).sum()) if missing_columns == 0 else len(actions)
    missing_core_fields = 0
    invalid_terminal_evidence = 0
    overdue_escalation_missing = 0
    if missing_columns == 0 and not actions.empty:
        missing_core_fields = int(
            (
                actions.action_id.astype(str).str.strip().eq("")
                | actions.action_key.astype(str).str.strip().eq("")
                | actions.owner_role.astype(str).str.strip().eq("")
                | actions.opened_month.astype(str).str.strip().eq("")
                | actions.due_month.astype(str).str.strip().eq("")
                | ~actions.priority.isin(["P1", "P2"])
            ).sum()
        )
        terminal = actions.status.isin(["Closed", "Cancelled"])
        terminal_month = actions.closed_month.astype(str).str.strip().ne("") | actions.cancelled_month.astype(str).str.strip().ne("")
        invalid_terminal_evidence = int((terminal & (~terminal_month | actions.closure_evidence.astype(str).str.strip().eq(""))).sum())
        overdue_escalation_missing = int((active.overdue & active.escalation_level.eq("None")).sum())

    required_keys = (
        set(current_required_actions.apply(action_key, axis=1)) if not current_required_actions.empty else set()
    )
    required_missing = len(required_keys - set(active.action_key))
    review_ids = set(review_history.review_id) if "review_id" in review_history else set()
    action_orphans = int(
        actions.apply(
            lambda row: _text(row.origin_review_id) not in review_ids or _text(row.review_id) not in review_ids,
            axis=1,
        ).sum()
    ) if not actions.empty else 0
    snapshot = action_history[action_history.snapshot_month.eq(end_month)] if "snapshot_month" in action_history else _empty(HISTORY_COLUMNS)
    snapshot_missing = len(set(actions.action_id) - set(snapshot.action_id))
    history_duplicate_rows = int(action_history.duplicated(["snapshot_month", "action_id"]).sum()) if not action_history.empty else 0
    review_history_duplicates = int(review_history.review_id.duplicated().sum()) if "review_id" in review_history else len(review_history)
    change_duplicate_ids = int(change_history.change_id.duplicated().sum()) if "change_id" in change_history else len(change_history)
    change_orphans = len(set(change_history.action_id) - set(actions.action_id)) if "action_id" in change_history else len(change_history)
    summary_missing = int(summary.empty or not summary.review_month.eq(end_month).all())
    status_reconciliation_gap = 0
    if not summary.empty:
        row = summary.iloc[0]
        status_reconciliation_gap = abs(
            int(row.total_actions)
            - int(row.open_actions)
            - int(row.in_progress_actions)
            - int(row.closed_actions)
            - int(row.cancelled_actions)
        )

    checks = {
        "management_lifecycle_missing_columns": int(missing_columns),
        "management_lifecycle_duplicate_ids": duplicate_ids,
        "management_lifecycle_duplicate_active_keys": duplicate_active_keys,
        "management_lifecycle_invalid_statuses": invalid_statuses,
        "management_lifecycle_missing_core_fields": missing_core_fields,
        "management_lifecycle_terminal_evidence_missing": invalid_terminal_evidence,
        "management_lifecycle_overdue_escalation_missing": overdue_escalation_missing,
        "management_lifecycle_required_actions_missing": required_missing,
        "management_lifecycle_action_orphans": action_orphans,
        "management_lifecycle_current_snapshot_missing": snapshot_missing,
        "management_lifecycle_history_duplicate_rows": history_duplicate_rows,
        "management_lifecycle_review_history_duplicates": review_history_duplicates,
        "management_lifecycle_change_duplicate_ids": change_duplicate_ids,
        "management_lifecycle_change_orphans": change_orphans,
        "management_lifecycle_summary_missing": summary_missing,
        "management_lifecycle_status_reconciliation_gap": int(status_reconciliation_gap),
    }
    checks["passed"] = all(value == 0 for value in checks.values())
    return checks
