from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import engine as base_engine
from .action_lifecycle import build_action_lifecycle, validate_action_lifecycle
from .engine_v16 import build as build_v16


VERSION = "0.17.0"


def _read_optional(path: str) -> pd.DataFrame:
    source = Path(path)
    return pd.read_csv(source, low_memory=False).fillna("") if source.exists() else pd.DataFrame()


def _write_csv(frame: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    """Run v0.16, then reconcile management actions with the persisted lifecycle."""
    previous_actions = _read_optional("data/processed/management_actions.csv")
    previous_review = _read_optional("data/processed/monthly_performance_review.csv")
    previous_action_history = _read_optional("data/processed/management_action_history.csv")
    previous_review_history = _read_optional("data/processed/performance_review_history.csv")
    previous_change_history = _read_optional("data/processed/management_action_changes.csv")

    result = build_v16(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    current_review = pd.read_csv("data/processed/monthly_performance_review.csv", low_memory=False)
    current_required = pd.read_csv("data/processed/management_actions.csv", low_memory=False)

    if previous_review_history.empty:
        previous_review_history = previous_review
    elif not previous_review.empty:
        previous_review_history = pd.concat([previous_review_history, previous_review], ignore_index=True)

    actions, action_history, review_history, changes, lifecycle_summary = build_action_lifecycle(
        current_required,
        current_review,
        end_month,
        previous_actions=previous_actions,
        action_history=previous_action_history,
        review_history=previous_review_history,
        change_history=previous_change_history,
    )
    lifecycle_checks = validate_action_lifecycle(
        actions,
        action_history,
        review_history,
        changes,
        current_required,
        lifecycle_summary,
        end_month,
    )

    with open("data/processed/performance_review_summary.csv", encoding="utf-8") as handle:
        review_summary = pd.read_csv(handle)
    review_summary = review_summary.drop(
        columns=[column for column in lifecycle_summary.columns if column != "review_month" and column in review_summary],
        errors="ignore",
    ).merge(lifecycle_summary, on="review_month", how="left")

    with open("data/processed/validation.json", encoding="utf-8") as handle:
        checks = json.load(handle)
    checks.update({key: value for key, value in lifecycle_checks.items() if key != "passed"})
    checks["passed"] = bool(checks.get("passed", False) and lifecycle_checks["passed"])
    if not checks["passed"]:
        raise RuntimeError(f"Management action lifecycle controls failed: {checks}")

    _write_csv(actions, "data/processed/management_actions.csv")
    _write_csv(action_history, "data/processed/management_action_history.csv")
    _write_csv(review_history, "data/processed/performance_review_history.csv")
    _write_csv(changes, "data/processed/management_action_changes.csv")
    _write_csv(review_summary, "data/processed/performance_review_summary.csv")
    with open("data/processed/validation.json", "w", encoding="utf-8") as handle:
        json.dump(checks, handle, indent=2)

    with open("web/data/dashboard.json", encoding="utf-8") as handle:
        dashboard = json.load(handle)
    dashboard["meta"]["version"] = VERSION
    dashboard["management_actions"] = base_engine._records(actions)
    dashboard["management_action_history"] = base_engine._records(action_history)
    dashboard["management_action_changes"] = base_engine._records(changes)
    dashboard["performance_review_summary"] = base_engine._records(review_summary)
    dashboard["validation"] = checks
    with open("web/data/dashboard.json", "w", encoding="utf-8") as handle:
        json.dump(dashboard, handle, separators=(",", ":"), allow_nan=False)

    overview = lifecycle_summary.iloc[0]
    with open("web/data/manifest.json", encoding="utf-8") as handle:
        manifest = json.load(handle)
    manifest.update(
        {
            "version": VERSION,
            "management_action_rows": int(len(actions)),
            "management_action_history_rows": int(len(action_history)),
            "management_action_change_rows": int(len(changes)),
            "open_management_actions": int(overview.open_actions),
            "in_progress_management_actions": int(overview.in_progress_actions),
            "closed_management_actions": int(overview.closed_actions),
            "cancelled_management_actions": int(overview.cancelled_actions),
            "overdue_management_actions": int(overview.overdue_actions),
            "carry_forward_management_actions": int(overview.carry_forward_actions),
            "p1_management_actions": int(overview.p1_active_actions),
            "executive_action_escalations": int(overview.executive_escalations),
            "validation": checks,
        }
    )
    with open("web/data/manifest.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    return result
