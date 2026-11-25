---
title: 'ADCM-8502 story 1: snapshot format, full shared setup and G1.01'
type: 'feature'
created: '2026-10-09'
status: 'in-review'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '6a94ae95ba14c31284b3aa02d04f47a877fb4a67'
context:
  - '{project-root}/_bmad-output/specs/spec-adcm-8502-tests/SPEC.md'
  - '{project-root}/_bmad-output/specs/spec-adcm-8502-tests/snapshot-format.md'
  - '{project-root}/_bmad-output/specs/spec-adcm-8502-tests/setup-features.md'
  - '{project-root}/_bmad-output/specs/spec-adcm-8502-tests/conventions.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Nothing pins the RBAC write-side state of `develop`, so phases 1–4 of ADCM-8502 cannot prove "snapshots identical, only query count differs".

**Approach:** Build the snapshot module (CAP-1), baseline + per-scenario diff goldens with missing-file recording (CAP-2), the full shared setup carrying every S-id (CAP-3) and the per-suite query-count file (CAP-7), proven end-to-end by G1.01. The point is to review the golden format before more scenarios land.

## Boundaries & Constraints

**Always:** SPEC.md constraints and `conventions.md`: no production code changes, `SETUP_WITH_RBAC`, write-side tables read directly, effective view computed in test code, no DB ids in goldens, rows sorted by natural key, goldens written only by the missing-file rule, superuser `admin` (no groups) drives the act step, typed code, no `_` helpers in test modules. No commits; stay on the current branch.

**Never:** Scenarios other than G1.01. Read-side helpers (`get_objects_for_user`, permission checks). A regeneration flag/env var. Asserting query counts. Real ansible runs.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Golden present, equal | unchanged code | test passes | N/A |
| Golden present, differs | a grant altered | fails; message names table and natural-key row(s) added/removed | AssertionError |
| Golden missing | file deleted | file written from current output; test fails "recorded, review it" | AssertionError |
| Dangling reference | row points to a deleted object | key `<dangling:type:key>`; key from the pre-act key map, else `#n` = rank of old pk among unresolved pks of that type | row kept |
| Unknown content type in a row | model without key rule | snapshot raises naming the model | RuntimeError |

**Decisions:**
- Goldens are YAML: `{table: {added: [...], removed: [...]}}` for diffs, `{table: [...]}` for the baseline; each row is one string `a | b | c`. Parsed and compared per table, so a failure names the table and rows.
- Spec kept as one story despite exceeding 1600 tokens (user).
- Two candidate baseline points exist: after `init_roles` + ADCM `init` (pre-setup, mostly the built-in role tree) and after the full shared setup (pre-test). This story commits only one baseline golden, taken after the full setup. Splitting into a separate post-init golden is deferred: the user decides it from the measured row counts (see Design Notes), not in this sprint.

</frozen-after-approval>

## Code Map

- `python/tests/suites.py` -- `ADCMDjangoAPISuiteNoBundles` (APIClient logged in as `admin`, `init_roles` + `init`); set `suite_setup = SETUP_WITH_RBAC` like `tests/cases/upgrade/test_bundle_switch.py`. `GenericTestCase` has no client, so it is not used.
- `python/tests/use_cases.py` -- `UseCases`: `upload_bundle`, `add_cluster/provider/host`, `add_host_to_cluster`, `add_services_to_cluster`, `set_hostcomponent`, `add_config_host_group`, `create_action_host_group`, `add_hosts_to_action_host_group`, `change_config`, `create_user`, `create_group`.
- `python/use_cases/transition/job/schedule.py:157,319` -- `ScheduleTask.do(action_orm, target, payload=RunActionDTO())` creates task + jobs and runs E4 `re_apply_policy_for_jobs`; get it from `cls.container(scope=dishka.Scope.REQUEST)` (see `api_v2/tests/test_internal.py:161`). Tasks are not executed.
- `python/use_cases/transition/host/duplicate.py` -- `create_duplicate(...)` for S-T3.
- `python/use_cases/logs/check.py` -- `AddCheckLogRecordForJob` (check log + E5). Custom log: `LogStorage` row + `rbac.roles.assign_view_logstorage_permissions_by_job`, exactly what `ansible_plugin/executors/custom_log.py:80` does.
- `python/rbac/services/policy.py` `policy_create`, `rbac/services/role.py` `role_create` -- policies and custom role (E7, real `Policy.apply`).
- `python/rbac/models.py` -- `Role` (TaskRole name `View role for task <id>` → replace with task key), `Policy.group/object/model_perm/group_object_perm`, `PolicyPermission`, `Group.display_name` (use it, `name` carries a type suffix). `guardian.models.GroupObjectPermission`.
- `python/rbac/upgrade/role.py:160-190` -- action role names (`Cluster Action: <display>`; hidden `<bundle>_<ver>_<edition>_..._<action>`): already id-free.
- `python/cm/models.py` -- `Host.original` (duplicates share fqdn), `JobLog.task`, `LogStorage(job, name, type)`.

## Tasks & Acceptance

**Execution:**
- [x] `python/tests/cases/rbac/__init__.py`, `python/tests/cases/rbac/bundles/{cluster_a_v1,cluster_a_v2,cluster_b,cluster_e,provider_v1,provider_v2}/config.yaml` -- bundles per Design Notes -- S-B1..B5 on FS.
- [x] `python/tests/cases/rbac/snapshot.py` -- typed, public first: `Snapshot` (tables + effective view, rows as natural-key tuples), `take_snapshot(key_map) -> Snapshot`, `collect_object_keys() -> key map`, `diff(before, after)`, `assert_matches_golden(case, path, actual)` (missing → write + fail "recorded, review it"), `record_query_count(path, scenario, count)` (read-modify-write, sorted) -- CAP-1, CAP-2, CAP-7.
- [x] `python/tests/cases/rbac/setup.py` -- `RBACWriteSideSuite(ADCMDjangoAPISuiteNoBundles)` with `setUpTestData` building every S-id (Design Notes), then `cls.key_map` and `cls.baseline`; `test_baseline` compares `cls.baseline` to `goldens/baseline.yaml`; a `run_act(scenario_id, act)` method snapshots after the act under `CaptureQueriesContext`, compares the diff to `goldens/<scenario_id>.yaml`, records the count -- CAP-3.
- [x] `python/tests/cases/rbac/test_g1_topology.py` -- `TestG1Topology(RBACWriteSideSuite)`: `test_g1_01_create_host_free`, `test_g1_01_create_host_in_cluster` via `POST /api/v2/hosts` (`hostproviderId`, `name`, `clusterId`) -- G1.01.
- [ ] `python/tests/cases/rbac/goldens/` -- recorded `baseline.yaml`, two G1.01 diffs, `query-counts/TestG1Topology.yaml`; reviewed by the user at the done checkpoint.
- [x] Spec Implementation Notes -- per-table row counts after init vs after full setup (Design Notes) -- input for the baseline split decision.

**Acceptance Criteria:**
- Given unchanged code and recorded goldens, when the suite runs twice with `--keepdb` (sequences advance, so ids differ), then both runs pass with no golden change.
- Given all goldens deleted, when the suite runs, then every test fails "recorded, review it"; a second run passes and `git diff` on goldens is empty.
- Given one baseline line edited, when `test_baseline` runs, then it fails naming the table and the row.
- Given the setup, when the baseline is read, then every S-id in `setup-features.md` is visible through its objects (Design Notes mapping), including a TaskRole of a rotated task and `<dangling:tasklog:...>` rows.

## Design Notes

**Object keys** (`type:key`): cluster/provider name; `service:A1/svc_1`; `component:A1/svc_1/comp_1`; host fqdn, duplicate `fqdn~dup#n` (rank among the original's duplicates); CHG/AHG `chg:<owner key>/<name>`; ConfigLog `<owner key>@rev<n>` (rank within owner); prototype `<bundle>-<ver>/<type>/<[service/]name>`; action `<prototype key>:<action>`; task `<target key>:<action>#<launch rank>`; job `<task key>/<order>`; log `<job key>/<name>:<type>`; role `<name>` (TaskRole → `task-role:<task key>`).

**Setup inventory:** Bundle A v1: svc_1..svc_3 × comp_1, comp_2; config and action `common` ("Common Action") on every level, host actions on cluster/service/component, CHG allowed. A v2: svc_3 removed, svc_4 added, svc_2/comp_2 removed, action `added` new, `removed` dropped; upgrades `plain` and `switch` (`bundle_switch`). B: "Common Action" on cluster and service, services svc_b1. P v1/v2: provider + host actions/config, plain upgrade. E (S-B5): one cluster action, cluster E1 + policy on its action role. Topology: A1, A2 (A v1, all services), B1; providers P1, P2; hosts free, in-cluster-unmapped, mapped to one component, mapped across svc_1+svc_2, plus hosts on A2/B1; one duplicate without cluster; CHGs on A1, A1/svc_1, A1/svc_1/comp_1, P1 with hosts and 2 revisions; AHGs on A1, svc_1, comp_1; ≥2 ConfigLogs on A1, svc_1, comp_1, P1, one host. Order: topology → task on A1 (unattached, S-J6) → groups/users/policies (R1–R8, G-* and U-* tables of `setup-features.md`) → tasks on every target type, host action on A1 targeting a host, AHG task, ADCM task → custom + check log on the A1 task → task on svc_1 rotated (TaskLog + orphan JobLogs deleted as `logrotate` does, S-J7).

Every built-in role row stays in `rbac_role_child`: E4/E6 mutate the built-in tree, so filtering would hide changes.

**Baseline split measurement (report only, nothing committed):** during implementation, take a snapshot right after `_initialize_roles_and_adcm()` (start of setup) and at the end of setup, and record per-table row counts for both points plus the delta in Implementation Notes. Present the table at the done checkpoint so the user can decide whether a separate post-init golden is needed. Remove any temporary measurement code afterwards.

## Implementation Notes

**Baseline split measurement** (per-table rows; temporary code removed):

| Table | After `init_roles` + `init` | After full setup | Delta |
|---|---|---|---|
| guardian_groupobjectpermission | 0 | 934 | 934 |
| rbac_policy_group_object_perm | 0 | 949 | 949 |
| auth_group_permissions | 0 | 102 | 102 |
| rbac_policypermission | 0 | 114 | 114 |
| rbac_role | 115 | 208 | 93 |
| rbac_role_child | 171 | 280 | 109 |
| rbac_policy_object | 0 | 25 | 25 |
| auth_user_groups | 0 | 11 | 11 |
| effective_object_perm | 0 | 726 | 726 |
| effective_model_perm | 0 | 43 | 43 |

Only `rbac_role` / `rbac_role_child` have post-init rows (286 of 3389 baseline rows).

User decision (2026-10-09): keep one baseline golden, no post-init split.

User decision (2026-10-09): `run_act(scenario_id, act)` replaced by the `self.act()` context manager; scenario id = test method name without `test_`. Arrange before the block, post-act asserts after it. Revisit the shape (e.g. a `@scenario` decorator over the whole test body) in each later story.

**Matrix coverage:** `test_snapshot.py` (`SimpleTestCase`, no DB; real golden files in a temp dir, ORM mocked for the unknown-model case) covers "golden differs" (baseline and diff formats), "golden missing" and "unknown content type". "Golden equal" and "dangling reference" are covered by `test_g1_topology.py` and the recorded baseline.

**Choices made inside the spec's room:**
- Key format: `<prefix>:<body>`; prefixes `cluster provider service component host adcm chg ahg config configlog prototype action task job log`. Nested keys embed the owner's full key (`configlog:chg:cluster:A1/chg-cluster@rev2`, `task:host:h-one:on_host#1`, `job:<task body>/<n>`, `log:<job body>/<name>:<type>`). TaskRole -> `task-role:<task key>`. Dangling -> `<dangling:<model>:<old body or #n>>`.
- Tables: `rbac_role` (`role | type`) and `rbac_role_child` are separate, so unattached TaskRoles (S-J6) show up. `rbac_policypermission` rows are `policy | group:<name>/user:<name> | perm`; a PolicyPermission linked to no policy gets `<no policy>`. Effective view = `effective_object_perm` + `effective_model_perm`.
- Diff golden lists only changed tables; an empty diff is `{}`.
- Setup key map = keys collected right before the S-J7 rotation merged with keys after setup, so rotated rows read `<dangling:tasklog:service:A1/svc_1:common#2>`.
- Launched tasks are set to `success` right after launch (not executed) so the same action can be launched again on the same object.
- ADCM task needs LDAP active: setup sets ADCM `ldap_integration` + `adcm_url` before launching `test_ldap_connection`.
- `G-idle` member: extra user `U-idle` (no other U-* is in `G-idle`).
- Query count uses `connection.execute_wrapper`: `CaptureQueriesContext` caps at 9000 and G1.01 in-cluster takes 9299 queries.
- `ContentType` cache is cleared before each act so query counts don't depend on test order.
- Base `RBACWriteSideSuite` raises `SkipTest` in `setUpClass` for itself (it is imported into test modules, so the loader collects it).

## Verification

**Commands:**
- `./run-tests.sh tests.cases.rbac` (repo root) -- first run: fails "recorded"; second and third runs: pass, goldens unchanged.
- `make pretty && make lint` -- clean.
