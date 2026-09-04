"""Release topology regression: no persistent publication before both test jobs pass."""
from pathlib import Path

import yaml


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/monthly-close.yml"


def jobs():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]


def test_publication_requires_both_independent_validation_jobs():
    workflow = jobs()
    assert "needs" not in workflow["build"]
    assert "needs" not in workflow["continuity"]
    assert set(workflow["publish"]["needs"]) == {"build", "continuity"}
    assert workflow["publish"]["if"] == "github.ref == 'refs/heads/main'"
    assert workflow["deploy"]["needs"] == ["publish"]
    assert workflow["deploy"]["if"] == "github.ref == 'refs/heads/main'"


def test_build_stages_same_run_candidate_without_persistent_publication():
    steps = jobs()["build"]["steps"]
    assert not any("git push" in step.get("run", "") for step in steps)
    assert not any("upload-pages-artifact" in step.get("uses", "") for step in steps)
    candidate = next(step for step in steps if step.get("uses") == "actions/upload-artifact@v4")
    assert candidate["if"] == "github.ref == 'refs/heads/main'"
    assert candidate["with"]["name"] == "finance-close-candidate"
    assert candidate["with"]["path"].split() == ["data/processed", "web"]
    assert candidate["with"]["if-no-files-found"] == "error"
    assert steps.index(candidate) > next(i for i, step in enumerate(steps)
                                        if step.get("run") == "python -m enterprise_finance.cli build")


def test_publish_uses_current_run_artifact_and_checks_revision_before_push():
    steps = jobs()["publish"]["steps"]
    download = next(step for step in steps if step.get("uses") == "actions/download-artifact@v4")
    # No run-id/repository override: the candidate must belong to this exact run.
    assert download["with"] == {"name": "finance-close-candidate", "path": "."}
    guard = next(step for step in steps if step.get("name") == "Reject superseded source revision")
    assert 'git fetch origin main' in guard["run"]
    assert 'test "$(git rev-parse origin/main)" = "$GITHUB_SHA"' in guard["run"]
    assert 'exit 1' in guard["run"]
    commit = next(step for step in steps if step.get("name") == "Commit generated finance data")
    assert "git add data/processed web/data" in commit["run"]
    assert "git push origin HEAD:main" in commit["run"]
    assert "--force" not in commit["run"]
    assert "git pull" not in commit["run"]
    upload = next(step for step in steps if step.get("uses") == "actions/upload-pages-artifact@v3")
    assert upload["with"]["path"] == "web"
    assert steps.index(download) < steps.index(guard) < steps.index(commit) < steps.index(upload)
    assert not any(step.get("continue-on-error") or "always()" in step.get("if", "") for step in steps)


def test_only_pull_request_runs_can_cancel_in_progress():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert workflow["concurrency"]["cancel-in-progress"] == "${{ github.event_name == 'pull_request' }}"
