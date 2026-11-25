---
title: 'ADCM-8502 story 2: G1 topology and object lifecycle scenarios'
type: 'feature'
created: '2026-10-09'
status: 'in-review'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '12791c2236067c1e6f82d978adf8e2990efbb8a8'
context:
  - '{project-root}/_bmad-output/specs/spec-adcm-8502-tests/SPEC.md'
  - '{project-root}/_bmad-output/specs/spec-adcm-8502-tests/scenarios.md'
  - '{project-root}/_bmad-output/specs/spec-adcm-8502-tests/conventions.md'
  - '{project-root}/_bmad-output/specs/spec-adcm-8502-tests/stories/1-snapshot-format-shared-setup-first-scenario.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Only G1.01 pins a non-RBAC trigger. Topology, lifecycle, upgrade, bundle and import triggers (G1.02–G1.10, G1.17, G1.18, G1.20) reach the RBAC write side unpinned.

**Approach:** Add one golden-diff test per scenario variant on top of the story 1 suite (CAP-4), driven through API where an endpoint exists, plugin executors / task runner for ansible and job paths. Empty diffs are recorded explicitly where no RBAC write is expected.

## Boundaries & Constraints

**Always:** SPEC.md constraints and `conventions.md`; story 1 machinery as is (`self.act()`, snapshot module, missing-file recording); no DB writes outside the `act()` block (the diff is baseline → after act, so arrange writes would land in it); preconditions come from the shared setup. No commits; current branch.

**Never:** Production code changes. Scenarios outside this story's ids. Real ansible. Asserting query counts. Explicit row asserts (those belong to G3).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Act with RBAC writes | any scenario below | golden diff recorded / matched | AssertionError names table + rows |
| Act without RBAC writes | G1.08 CHG host add/remove | golden is `{}` | same |
| Act fails functionally | API non-2xx, plugin `CallResult.error`, task not `success` | test fails before the snapshot, with the response/error | AssertionError |

**Decisions:**
- Shared setup is extended (Design Notes) instead of arranging inside tests; `baseline.yaml` and both G1.01 goldens are re-recorded and reviewed again (user).
- Spec kept as one story despite exceeding 1600 tokens (user).
- G1.20: `load` crashes on `develop` (`create_host` builds `StatusScenarios()` without `cluster_service`; `create_cluster` calls `set_host_component_mapping` without `cluster_service`). The test pins the expected error instead of patching around it, so it fails once `load` is fixed and is then turned into a golden-diff scenario. No G1.20 golden until then (user).
- Snapshot module: ConfigLogs whose owner is deleted get no current key and render as `<dangling:configlog:<pre-act key>>` (user accepted the change to story 1 machinery).

</frozen-after-approval>

## Code Map

- `python/tests/cases/rbac/setup.py` -- `RBACWriteSideSuite`: `act()`, `launch_action` (finished tasks: status `success`), `service`/`component`/`role` lookups, `hosts` dict. Setup tasks give plugin contexts: `common` on A1 (S-J1, second launch) and on P1.
- `python/tests/cases/rbac/test_g1_topology.py` -- existing G1.01; story 2 tests go here (one suite = one setup build).
- `python/tests/suites.py:198` -- `ADCMPluginExecutorSuite.prepare_executor`: builds executor from a `JobLog` context. Our suite can't inherit it (its `setUpTestData` adds bundles/objects).
- `python/ansible_plugin/executors/` -- `add_host.py` (provider ctx), `add_host_to_cluster.py`, `remove_host_from_cluster.py`, `delete_service.py` (mapping + `DeleteService`), `hostcomponent.py` (rejects actions with `hc_acl`).
- `python/tests/task_flow.py` -- `self.task_runner().launch_task(task_id)`: ansible jobs mocked, internal scripts (`hc_apply`, `service_manage`) real, finalizer real. Pattern: `run_upgrade` in `tests/cases/upgrade/test_bundle_switch.py:55`.
- API v2: `POST hosts/{id}/duplicates` (`name`, `clusterId`); `POST/DELETE clusters/{id}/hosts`; `POST clusters/{id}/services`; `DELETE clusters/{id}/services/{id}` (refused if mapped/not `created`); `POST/DELETE clusters/{id}/config-groups[/{id}/hosts]`; `POST clusters/{id}/mapping` (full mapping); `POST clusters/{id}/actions/{id}/run` (`hostComponentMap`); `POST clusters|hostproviders/{id}/upgrades/{id}/run`; `POST bundles` multipart (`tests/use_cases.py:285` `prepare_bundle_file`), `DELETE bundles/{id}`; `DELETE clusters|hostproviders|hosts/{id}` (host: not in cluster; provider: no hosts).
- `python/cm/legacy/services/transition/{dump,load}.py` -- `dump(cluster_id) -> TransitionPayload`, `load(data, report)`; `load` builds its own container from `get_main_providers()` (real status/celery providers).

## Tasks & Acceptance

**Execution:**
- [x] `python/tests/suites.py` -- extract `prepare_executor` body into public `prepare_plugin_executor(container, executor_type, call_arguments, call_context)`; method delegates -- reuse without inheriting the suite.
- [x] `python/tests/cases/rbac/bundles/cluster_a_v1/config.yaml`, new `bundles/cluster_f/config.yaml` -- per Design Notes (setup extension).
- [x] `python/tests/cases/rbac/setup.py` -- setup extension per Design Notes; `run_plugin(executor_type, arguments, job)` asserting no error; `run_action_via_api(owner, action_name, payload)` = API run + `task_runner().launch_task` + `success` assert.
- [x] `python/tests/cases/rbac/test_g1_topology.py` -- tests per Design Notes table.
- [x] `python/tests/cases/rbac/goldens/` -- new goldens + query counts recorded; baseline/G1.01 re-recorded.

**Acceptance Criteria:**
- Given recorded goldens, when `./run-tests.sh tests.cases.rbac` runs twice with `--keepdb`, then all tests pass and no golden changes.
- Given all goldens deleted, when the suite runs, then every test fails "recorded, review it" and the next run passes with an empty `git diff` against the first recording.
- Given G1.08 host add/remove, when recorded, then each golden is `{}`.

## Design Notes

Setup extension: A v1 cluster gets `svc_spare` (one component, never added) and actions `hc_finalize` (`hc_acl` add/remove `svc_1/comp_2`, ansible only), `hc_apply` (same `hc_acl`, ansible + internal `hc_apply`), `add_spare` (internal `service_manage` adding `svc_spare`). Provider `P3` (no hosts) in policy `P-empty-provider` (Provider Administrator, `G-empty`). `cluster_f`: new bundle with "Common Action" + "F Action".

| Test (`test_` + id) | Act |
|---|---|
| g1_02_create_host_plugin | `adcm_add_host` in P1 job |
| g1_03_duplicate_host_free / _in_cluster | duplicate `h-free`, no cluster / `clusterId`=A1 |
| g1_04_add_host_to_cluster_one / _many / _plugin | `h-free`; `h-free`+`h-free-p2`; plugin in A1 job |
| g1_05_remove_host_from_cluster / _plugin | `h-unmapped` (API; plugin in A1 job) |
| g1_06_add_service / _service_manage | `svc_spare` to A1 (API; `add_spare` run) |
| g1_07_delete_service / _plugin | API `svc_3` of A1; plugin `svc_1` of A1 (mapped, has tasks → `keep_objects`) |
| g1_08_create_chg / _delete_chg / _add_chg_host / _remove_chg_host | on A1 `chg-cluster`: add `h-multi`, remove `h-one` |
| g1_09_mapping_add / _remove / _move / _plugin / _hc_finalize / _hc_apply | A1: `h-unmapped`→comp_2; drop `h-one`; `h-one` comp_1→comp_2; `adcm_hc` in A1 job; action runs with `hostComponentMap` |
| g1_10_upgrade_cluster / _provider | `plain` on A1 / P1 |
| g1_17_upload_bundle / _delete_bundle | upload `cluster_f`; delete A v2 (unused) |
| g1_18_delete_cluster / _provider / _host | A2 / P3 / `h-free` |
| g1_20_import_cluster | `load(dump(A1))` with cluster renamed `A1-imported`, hosts prefixed `imp-`; `get_main_providers` patched to the suite's "with-rbac" providers so status/RBAC wiring matches the suite |

Act-step shape: keep `with self.act():` (memory: revisit per story); the decorator form gains nothing here since every test has arrange-free acts.

## Verification

**Commands:**
- `./run-tests.sh tests.cases.rbac` -- first run fails "recorded" for new/deleted goldens; second and third runs pass, goldens unchanged.
- `make pretty && make lint` -- clean.

## Implementation Notes

**Raised (production defects, not fixed):** `cm.legacy.services.transition.load.load` crashes on `develop`:
`api_v2.host.utils.create_host` builds `StatusScenarios()` without its required `cluster_service` (first crash), and
behind it `create_cluster` calls `set_host_component_mapping` without `cluster_service`. Per the Decisions block,
`test_g1_20_import_cluster` keeps the dump + rename and the `get_main_providers` patch, and asserts `load` raises
`TypeError` mentioning `cluster_service`, outside `self.act()`. No G1.20 golden or query count; once `load` is fixed the
assertion goes and the call moves into `self.act()` with a golden.

**Story 1 machinery touched (snapshot module, one rule):** ConfigLogs outlive their deleted owner (cluster/service
deletion), so `collect_object_keys` produced duplicate `<no owner>@revN` keys and raised. ConfigLogs whose owner is gone
now get no current key and render as dangling with their pre-act key (`<dangling:configlog:cluster:A2@rev1>`).
Baseline is unaffected (it had no ownerless ConfigLogs).

**Choices made inside the spec's room:**
- `a1_job` / `p1_job` (S-J1 jobs of A1 and P1 `common`) are kept on the suite as plugin contexts.
- `A1_MAPPING` constant (setup mapping of A1, reused by `build_topology`) and `mapping_payload(cluster, entries)` act
  helper build mapping / `hostComponentMap` payloads.
- G1.04 plugin passes `host_id`: `h-free` has a duplicate with the same fqdn, lookup by fqdn is ambiguous.
- G1.09 `_add`, `_plugin`, `_hc_finalize`, `_hc_apply` all add `h-unmapped` to `svc_1/comp_2`, so the paths compare.
- G1.17 archive is built in the suite's temp dir (in downloads the upload is refused as already uploaded).
- `cluster_f` bundle: `common` ("Common Action") + `f_action` ("F Action").

**Recorded observations for review:** G1.03 duplicate without cluster and both G1.08 CHG host changes are `{}`;
G1.08 delete CHG drops rows with 17 queries (cascade). G1.20 pins the `load` crash, no diff recorded.

## Spec Change Log

## Review Triage Log
