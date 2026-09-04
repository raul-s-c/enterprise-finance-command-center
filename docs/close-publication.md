# Validated close publication

The monthly close keeps Python/unit/frontend validation and the full consecutive-close regression in independent jobs. Neither job changes the repository or publishes Pages.

The build job uploads a short-lived `finance-close-candidate` artifact containing `data/processed` and `web`, preserving their repository-relative paths. On main only, the `publish` job waits for **both** validation jobs to succeed, downloads the candidate from the same workflow run, and verifies that the triggering source SHA is still the head of main.

Only then does it commit generated files and upload the Pages artifact. Deployment depends on successful publication. Failed, cancelled or skipped prerequisite jobs cannot publish data or deploy. Pull requests validate the workflow topology but cannot publish.

A source update while validation is running fails the stale-revision check. An update between that check and the push is rejected by the normal non-fast-forward Git push; there is no force push or automatic merge of stale outputs. Re-run the close against the current main revision after checking the failure. Production runs are not automatically cancelled.

Git data publication and Pages deployment are separate operations, not an atomic transaction: a Pages failure can leave validated data committed while the previous site remains live. The deployment monitor must continue checking both workflow completion and the public manifest. A candidate artifact expires after three days; beyond that, rebuild from current main rather than reusing an expired candidate.

This infrastructure change retains engine version 0.21.0, all finance controls and financial tolerances. Regression tests in `tests/test_publication_workflow.py` enforce dependency ordering, main-only publication, same-run artifact selection, stale-source rejection and non-forced publication.
