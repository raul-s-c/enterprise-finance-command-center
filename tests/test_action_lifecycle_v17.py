import pandas as pd

from enterprise_finance.action_lifecycle import (
    build_action_lifecycle,
    validate_action_lifecycle,
)


def _review(month: str, review_id: str, required: bool = True) -> dict:
    return {
        "review_id": review_id,
        "review_month": month,
        "scope_level": "Group",
        "entity": "All",
        "division": "All",
        "category": "Monthly P&L vs Budget",
        "metric": "EBIT",
        "comparison": "Budget",
        "unit": "EUR",
        "actual_value": 80.0,
        "benchmark_value": 100.0,
        "variance": -20.0,
        "materiality_pct": 0.2,
        "favorable": False,
        "severity": "Critical",
        "action_required": required,
        "source_dataset": "budget_performance.csv",
        "source_key": f"{month}|All|All|ebit",
        "headline": "Group EBIT missed budget.",
        "explanation": "Source-tied test observation.",
    }


def _new_action(month: str, review_id: str, due_month: str) -> dict:
    return {
        "action_id": review_id.replace("REV-", "ACT-"),
        "review_id": review_id,
        "review_month": month,
        "scope_level": "Group",
        "entity": "All",
        "division": "All",
        "priority": "P1",
        "owner_role": "CFO",
        "due_month": due_month,
        "status": "Open",
        "action": "Own the EBIT recovery bridge.",
        "expected_outcome": "Return EBIT to budget.",
        "trigger_metric": "EBIT",
        "trigger_value": -20.0,
        "source_dataset": "budget_performance.csv",
    }


def test_action_is_carried_forward_with_stable_id_and_overdue_escalation():
    august_review = pd.DataFrame([_review("2026-08", "REV-202608-EBIT")])
    august_new = pd.DataFrame([_new_action("2026-08", "REV-202608-EBIT", "2026-09")])
    august = build_action_lifecycle(august_new, august_review, "2026-08")

    september_review = pd.DataFrame([_review("2026-09", "REV-202609-EBIT")])
    september_new = pd.DataFrame([_new_action("2026-09", "REV-202609-EBIT", "2026-10")])
    september = build_action_lifecycle(
        september_new,
        september_review,
        "2026-09",
        previous_actions=august[0],
        action_history=august[1],
        review_history=august[2],
        change_history=august[3],
    )
    october_review = pd.DataFrame([_review("2026-10", "REV-202610-EBIT")])
    october_new = pd.DataFrame([_new_action("2026-10", "REV-202610-EBIT", "2026-11")])
    actions, history, reviews, changes, summary = build_action_lifecycle(
        october_new,
        october_review,
        "2026-10",
        previous_actions=september[0],
        action_history=september[1],
        review_history=september[2],
        change_history=september[3],
    )

    action = actions.iloc[0]
    assert action.action_id == "ACT-202608-EBIT"
    assert action.opened_month == "2026-08"
    assert action.last_seen_month == "2026-10"
    assert action.occurrence_count == 3
    assert bool(action.overdue)
    assert action.overdue_months == 1
    assert action.escalation_level == "Executive"
    assert action.carry_forward_months == 2
    assert set(history.snapshot_month) == {"2026-08", "2026-09", "2026-10"}
    assert set(changes.change_type) == {"Created", "Carried Forward"}
    checks = validate_action_lifecycle(actions, history, reviews, changes, october_new, summary, "2026-10")
    assert checks["passed"], checks


def test_resolved_trigger_closes_action_with_evidence_and_is_idempotent():
    august_review = pd.DataFrame([_review("2026-08", "REV-202608-EBIT")])
    august_new = pd.DataFrame([_new_action("2026-08", "REV-202608-EBIT", "2026-09")])
    first = build_action_lifecycle(august_new, august_review, "2026-08")
    september_review = pd.DataFrame([_review("2026-09", "REV-202609-EBIT", required=False)])

    closed = build_action_lifecycle(
        pd.DataFrame(columns=august_new.columns),
        september_review,
        "2026-09",
        previous_actions=first[0],
        action_history=first[1],
        review_history=first[2],
        change_history=first[3],
    )
    action = closed[0].iloc[0]
    assert action.status == "Closed"
    assert action.closed_month == "2026-09"
    assert "no longer requires action" in action.closure_evidence
    checks = validate_action_lifecycle(closed[0], closed[1], closed[2], closed[3], pd.DataFrame(), closed[4], "2026-09")
    assert checks["passed"], checks

    repeated = build_action_lifecycle(
        pd.DataFrame(columns=august_new.columns),
        september_review,
        "2026-09",
        previous_actions=closed[0],
        action_history=closed[1],
        review_history=closed[2],
        change_history=closed[3],
    )
    assert len(repeated[1]) == len(closed[1])
    assert len(repeated[3]) == len(closed[3])


def test_control_rejects_duplicate_active_actions_and_missing_terminal_evidence():
    review = pd.DataFrame([_review("2026-08", "REV-202608-EBIT")])
    incoming = pd.DataFrame([_new_action("2026-08", "REV-202608-EBIT", "2026-09")])
    actions, history, reviews, changes, summary = build_action_lifecycle(incoming, review, "2026-08")
    duplicate = pd.concat([actions, actions], ignore_index=True)
    duplicate.loc[1, "action_id"] = "ACT-DUPLICATE"
    duplicate.loc[1, "status"] = "Closed"
    duplicate.loc[1, "closed_month"] = ""
    duplicate.loc[1, "closure_evidence"] = ""

    checks = validate_action_lifecycle(duplicate, history, reviews, changes, incoming, summary, "2026-08")
    assert not checks["passed"]
    assert checks["management_lifecycle_terminal_evidence_missing"] == 1


def test_persisted_owner_and_status_edits_are_audited_and_recurrence_gets_a_new_cycle():
    august_review = pd.DataFrame([_review("2026-08", "REV-202608-EBIT")])
    august_new = pd.DataFrame([_new_action("2026-08", "REV-202608-EBIT", "2026-09")])
    first = build_action_lifecycle(august_new, august_review, "2026-08")
    edited = first[0].copy()
    edited.loc[0, "owner_role"] = "Group CFO"
    edited.loc[0, "status"] = "Cancelled"
    edited.loc[0, "cancelled_month"] = "2026-09"
    edited.loc[0, "closure_evidence"] = "Executive committee replaced the initiative."
    september_review = pd.DataFrame([_review("2026-09", "REV-202609-EBIT")])
    september_new = pd.DataFrame([_new_action("2026-09", "REV-202609-EBIT", "2026-10")])

    actions, history, reviews, changes, summary = build_action_lifecycle(
        september_new,
        september_review,
        "2026-09",
        previous_actions=edited,
        action_history=first[1],
        review_history=first[2],
        change_history=first[3],
    )

    assert len(actions) == 2
    assert set(actions.status) == {"Open", "Cancelled"}
    assert actions.action_id.nunique() == 2
    assert "Field Changed" in set(changes.change_type)
    assert "Status Changed" in set(changes.change_type)
    checks = validate_action_lifecycle(actions, history, reviews, changes, september_new, summary, "2026-09")
    assert checks["passed"], checks


def test_v16_register_is_migrated_with_an_audited_schema_event():
    review = pd.DataFrame([_review("2026-08", "REV-202608-EBIT")])
    legacy = pd.DataFrame([_new_action("2026-08", "REV-202608-EBIT", "2026-09")])
    actions, history, reviews, changes, summary = build_action_lifecycle(
        legacy,
        review,
        "2026-08",
        previous_actions=legacy,
        review_history=review,
    )

    assert set(changes.change_type) == {"Migrated"}
    assert actions.iloc[0].origin_review_id == "REV-202608-EBIT"
    checks = validate_action_lifecycle(actions, history, reviews, changes, legacy, summary, "2026-08")
    assert checks["passed"], checks
