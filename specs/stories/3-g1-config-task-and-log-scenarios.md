---
title: 'ADCM-8502 story 3: G1 config, task and log scenarios'
type: 'feature'
created: '2026-10-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '5c1719fb1988f37f7f9893e6efbdbe786b347262'
context:
  - '{project-root}/_bmad-output/specs/spec-adcm-8502-tests/SPEC.md'
  - '{project-root}/_bmad-output/specs/spec-adcm-8502-tests/scenarios.md'
  - '{project-root}/_bmad-output/specs/spec-adcm-8502-tests/conventions.md'
  - '{project-root}/_bmad-output/specs/spec-adcm-8502-tests/stories/2-g1-topology-and-object-lifecycle-scenarios.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Config saves (E3), task launches (E4), custom/check logs (E5), `bundle_switch`/`bundle_revert` upgrades and logrotate reach the RBAC write side unpinned: G1.11–G1.16 and G1.19 have no tests.

**Approach:** Add one golden-diff test per scenario variant to the story 1/2 suite (CAP-4): API where an endpoint exists, plugin executors / lookup / task runner for job paths. Tasks launched in the act are not executed unless the scenario needs their internal scripts.

## Boundaries & Constraints

**Always:** SPEC.md constraints and `conventions.md`; story 1/2 machinery as is (`self.act()`, snapshot module, missing-file recording, `run_plugin`, `run_action_via_api`); no DB writes outside the `act()` block; preconditions come from the shared setup. No commits; current branch.

**Never:** Production code changes. Scenarios outside G1.11–G1.16, G1.19. Real ansible. Asserting query counts. Explicit row asserts (G3).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Act with RBAC writes | any scenario below | golden diff recorded / matched | AssertionError names table + rows |
| Act without E5 | second check log of a job that already has one | golden recorded as is (expected `{}`) | same |
| Act fails functionally | API non-2xx, plugin `CallResult.error`, executed task not `success`, `PluginResult.changed` false | test fails before the snapshot | AssertionError |

**Decisions:**
- `revert_upgrade` action (`bundle_revert`) added to A v2; wizard lives in a new bundle `cluster_w` + cluster `W1` + policy `P-wizard` (Cluster Administrator on W1, new group `G-wizard`, no users). Baseline re-recorded; story 2 goldens that change (expected: `g1_10_upgrade_cluster`, `g1_17_delete_bundle`) are re-recorded and listed for review (user).
- Spec kept as one story despite exceeding 1600 tokens (user).

</frozen-after-approval>

## Code Map

- `python/tests/cases/rbac/setup.py` -- `RBACWriteSideSuite`: `act()`, `run_plugin`, `run_action_via_api` (API run + `task_runner().launch_task` + `success`), `a1_job`/`p1_job` (A1/P1 `common` jobs; `a1_job` already has custom log `custom` and a check log), `hosts`, `service`/`component`/`role`. AHGs `ahg-cluster/-service/-component` (owners A1, A1/svc_1, A1/svc_1/comp_1), CHG `chg-cluster`. ADCM LDAP config set in setup, so `test_ldap_connection` can launch.
- `python/tests/cases/rbac/bundles/cluster_a_v2/config.yaml` -- `switch` upgrade (`bundle_switch`) already present.
- Revert flow: `python/tests/cases/upgrade/test_bundle_revert.py:60-90` (`plain` upgrade via API, then `revert_upgrade` action run + `launch_task`); bundle shape `tests/cases/upgrade/bundles/bundle_revert/cluster_v2/config.yaml`.
- Switch flow: `tests/cases/upgrade/test_bundle_switch.py:55` `run_upgrade` (API 200 → `launch_task` → `success`).
- Config API: `POST {object}/configs` and `POST {owner}/config-groups/{id}/configs` with `{"config", "adcmMeta", "description"}` (`api_v2/tests/test_upgrade.py:736`).
- `ansible_plugin/executors/config.py` `ADCMConfigPluginExecutor` (`UpdateConfigurationFromJob`); needs `cm.legacy.services.job.run.create_related_configs(job_id, owner, config_repo)` first, as `ansible_plugin/tests/test_adcm_config.py:61`.
- `ansible_collections/arenadata/adcm/plugins/lookup/adcm_config.py:110` `call_adcm_config_lookup(terms, variables, kwargs)` (legacy E3 import); `variables={"job": {"id", "action"}, "cluster": {"id"}}` as `tests/cases/lookup/test_adcm_config.py:782`.
- Runs: `self.client.v2[obj, "actions", action, "run"]` for cluster/service/component/provider/host and host actions (on `Host`, `api_v2/tests/test_actions.py:380`), AHG (`v2[ahg, "actions", action, "run"]`), ADCM (`v2["adcm", "actions", action, "run"]`).
- Wizard: `POST {owner}/actions/{id}/processes` then `POST .../processes/{id}/steps` submit `{"method": "submit", "params": {"processSyncKey", "stepId"}}` (`api_v2/tests/base.py:174-255`, `test_wizard/test_process_execution.py:274`); operation-first template + python `scripts_template` as `api_v2/tests/bundles/wizard_action/wizard_jinja/{stages_operation_first.j2,steps/s3_script.py}`. E4 at `use_cases/wizard.py:388`.
- `ansible_plugin/executors/custom_log.py` `ADCMCustomLogPluginExecutor[...]` (configured via `[lambda _, path: str(path)]`, `ansible_plugin/tests/test_adcm_custom_log.py:25`), `check.py` `ADCMCheckPluginExecutor` (E5 on the first check log of a job only).
- `cm/management/commands/logrotate.py` -- `call_command("logrotate", "--target=all")`; defaults: jobs 365 days in DB/FS, config rotation off; deletes `success`/`failed` TaskLogs older than threshold, then JobLogs without task.

## Tasks & Acceptance

**Execution:**
- [x] `python/tests/cases/rbac/bundles/` -- `revert_upgrade` in `cluster_a_v2`; new `cluster_w` (wizard, operation-first step, python `scripts_template`).
- [x] `python/tests/cases/rbac/setup.py` -- upload `cluster_w`, cluster `W1`, group `G-wizard`, policy `P-wizard`; `run_upgrade_via_api(owner, upgrade)` (204 or 200 + `launch_task` + `success`).
- [x] `python/tests/cases/rbac/test_write_side.py` -- tests of the Design Notes table in the single suite `TestRBACWriteSide` (see Spec Change Log).
- [x] `python/tests/cases/rbac/goldens/` -- new goldens + query counts recorded; baseline and affected story 2 goldens re-recorded.

**Acceptance Criteria:**
- Given recorded goldens, when `./run-tests.sh tests.cases.rbac` runs twice, then all tests pass and no golden changes.
- Given all goldens deleted, when the suite runs, then every test fails "recorded, review it" and the next run passes with an empty `git diff` against the first recording.

## Design Notes

| Test (`test_` + id) | Act |
|---|---|
| g1_11_upgrade_switch | `switch` upgrade on A1, task executed |
| g1_11_upgrade_revert | `plain` upgrade on A1, then `revert_upgrade` run and executed (net diff) |
| g1_12_config_cluster / _host / _chg | API config save on A1 / `h-one` / `chg-cluster` |
| g1_12_config_plugin | `create_related_configs` + `adcm_config` plugin (`type: cluster`) in `a1_job` |
| g1_12_config_lookup | `adcm_config` lookup on cluster in `a1_job` |
| g1_13_launch_cluster / _service / _component / _provider / _host | API run `common` on A1, A1/svc_1, A1/svc_1/comp_1, P1, `h-one` |
| g1_14_host_action_cluster / _service / _component | API run `on_host` of A1 / svc_1 / comp_1 on `h-one` |
| g1_14_ahg_cluster / _service / _component | API run `in_ahg` on the three AHGs |
| g1_14_adcm_action | API run ADCM `test_ldap_connection` |
| g1_15_wizard | start process + submit operation step (task launched, not executed) |
| g1_16_custom_log | custom log `g1-16` in `a1_job` |
| g1_16_check_log_first / _next | check log in `p1_job` (first) / `a1_job` (already has one) |
| g1_19_logrotate | `logrotate --target=all` with `django.utils.timezone.now` patched to +366 days (rotates all finished setup tasks without arrange writes) |

C9 (ADCM task gets no E4 grant) is pinned by `g1_14_adcm_action`'s golden. Act-step shape: keep `with self.act():` — multi-call acts (revert, wizard) still read well inside one block.

## Verification

**Commands:**
- `./run-tests.sh tests.cases.rbac` -- first run fails "recorded" for new/re-recorded goldens; second and third runs pass, goldens unchanged.
- `make pretty && make lint` -- clean.

## Implementation Notes

**Deviations from the Code Map (code is the truth):**
- Wizard submit endpoint is `POST {owner}/actions/{id}/processes/{id}/operation` (as `api_v2/tests/base.py` `submit_step_r`), not `.../steps`.
- An operation step in `cluster_w/stages.j2` needs `ui_options` (upload of the process fails with "Field required" otherwise).
- `g1_12_config_lookup` also calls `create_related_configs` in the act: the lookup ends in `update_related_configs`,
  which expects the job's related configs prepared at job start (same as `tests/cases/lookup` `prepare_job`).
- `TaskOwner` for `create_related_configs` comes from `JobRepo().get_task(a1_job.task_id).owner` (read before the act).

**Setup / story 2 goldens re-recorded (review):** `baseline.yaml` gains W1 / `G-wizard` / `P-wizard` rows, roles
"Cluster Action: Revert Upgrade" and "Cluster Action: Wizard Action" (children of Cluster Administrator).
`G-wizard` also gets `view_logstorage` on A1's setup custom/check logs (same-role spread, C7).
`g1_10_upgrade_cluster` gains the `revert_upgrade` grants for Cluster Administrator policies on A1;
`g1_17_delete_bundle` additionally removes the revert-upgrade roles. No other story 2 golden changed.

**Recorded observations for review:** `g1_16_check_log_next` is `{}`; `g1_14_adcm_action` adds only the ADCM
TaskRole, no grants (C9); `g1_19_logrotate` deletes no RBAC rows: GOPs, policy rows, TaskRoles and their
role links of rotated tasks stay and render as `<dangling:...>` (D6); `g1_11_upgrade_revert` is the net diff of plain upgrade + revert.

## Spec Change Log

- User feedback after implementation: all scenarios must be one suite so the setup is built once. Amended: `test_g1_topology.py` (`TestG1Topology`) and `test_g1_tasks.py` (`TestG1Tasks`) merged into `test_write_side.py` / `TestRBACWriteSide`, sections in G1 id order; query counts now in `goldens/query-counts/TestRBACWriteSide.yaml`. Avoids: a second setup build per extra class. KEEP: test names and goldens unchanged.

## Review Triage Log
