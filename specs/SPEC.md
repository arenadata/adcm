---
id: SPEC-adcm-8502-tests
companions: [snapshot-format.md, setup-features.md, scenarios.md, conventions.md, ../../ADCM-8502/01-call-sites.md, ../../ADCM-8502/02-task-role.md]
sources: [../../ADCM-8502/problem.md, ../../ADCM-8502/clarifications.md, ../../ADCM-8502/03-equivalence-suite.md, ../../ADCM-8502/04-plan.md]
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# RBAC write-side equivalence suite (ADCM-8502, Phase 0)

## Why

The RBAC write side (policy application, permission materialization) is slow by implementation. Cluster hierarchies are the worst case, and task history makes it grow without bound. The planned fixes (single `RBACScenarios` seam, `Policy.apply` preload, call-site dedup, isolated hot spots) must not change the materialized permissions. Today nothing pins that state: existing tests check performance or single endpoints, not case equality. Several current behaviours are also quirky or defective (C1–C9, D1–D7 in `02-task-role.md`, ⚠ cases in `01-call-sites.md` §2.1). This story pins the current write-side state of `develop`, so every later phase can prove "snapshots identical, only query count differs".

## Capabilities

- **CAP-1**
  - **intent:** A test can capture the RBAC write-side state as an id-independent snapshot, plus a derived per-user effective view.
  - **success:** The same scenario run on two databases with different id sequences gives byte-identical serialized snapshots. Rows referencing deleted objects show up as `<dangling:...>` keys and are not dropped (`snapshot-format.md`).

- **CAP-2**
  - **intent:** The suite compares each scenario against committed goldens: one baseline snapshot after the shared setup, plus a per-scenario diff of added and removed rows.
  - **success:** On unchanged code every scenario passes. A deliberately altered grant fails, and the failure output names the table and natural-key row. A missing golden is recorded from the current output and the test fails with a "recorded, review it" message. Deleting all goldens and re-recording them on unchanged code produces no file changes.

- **CAP-3**
  - **intent:** One shared setup carries every setup feature (S-id) the scenarios need: bundles, topology, tasks/logs, policies, groups, users.
  - **success:** Every S-id in `setup-features.md` maps to concrete setup objects, and the setup builds deterministically on current code (the baseline golden is stable across runs).

- **CAP-4**
  - **intent:** Every non-RBAC trigger that reaches the RBAC write side (topology, config, tasks, logs, bundles, upgrade, import) has a scenario that pins its effect.
  - **success:** G1.01–G1.20 in `scenarios.md` each have a passing test driven at the agreed level, with a golden diff.

- **CAP-5**
  - **intent:** Every RBAC-object change (policy, role, group, user membership) has a scenario that pins its effect, including the per-user effective view.
  - **success:** G2.01–G2.07 in `scenarios.md` each have a passing test with a golden diff. G2.07 shows unchanged write-side tables and an effective-view diff equal to the grants no other group of that user still provides.

- **CAP-6**
  - **intent:** Each known quirk, defect or unverified suspicion has a test that confirms its current behaviour, so it can later be kept or changed on purpose.
  - **success:** G3.01–G3.17 each have a passing test that asserts the case's specific rows. Every C1–C9, D1–D7 and `01-call-sites.md` §2.1 ⚠ case is referenced by at least one G3 test. The mark column in `scenarios.md` is present and left unset.

- **CAP-7**
  - **intent:** Each scenario records its query count, so phases 1–4 have a baseline to measure against.
  - **success:** A run writes the query count of every scenario's act step to one separate file per suite. That file is never compared.

## Constraints

- No production code changes: the suite pins `develop` as it is. A code change found necessary to make something testable is raised, not made.
- Suites run with `SETUP_WITH_RBAC` (real `RBACScenarios`). `RBACScenariosDummy` would pin nothing.
- Snapshots read the write-side tables directly. The effective view is computed in test code from those tables, never through read-side helpers (`get_objects_for_user`, permission checks): the read side is out of scope.
- Goldens are written only by the missing-file rule: no regeneration flag, env var or command. To update a golden, delete it and rerun.
- Goldens contain no DB ids. Rows are sorted by natural key, so diffs are deterministic.
- Driving level: API (`APIClient`) where an endpoint exists. Use cases or plugin executors for ansible and job paths (G1.02, .09, .11, .12, .16). No real ansible runs.
- One shared setup per suite, built in `setUpTestData`, with per-test rollback. Only the act step is per scenario.
- A superuser in no group drives scenarios, so it never appears in snapshots.
- Test style follows `conventions.md`.

## Non-goals

- Phases 1–4 of `04-plan.md` (seam routing, preload, dedup, hot-spot fixes) and anything in its §3 (TaskRole redesign, incremental grants).
- Deciding the "preserve / intentional change" marks for G3, or fixing D1–D7.
- Read-side behaviour: permission checks, queryset filtering, API visibility.
- Cost measurement with large task history (`02-task-role.md` §6.1), production sizing, profiler changes.
- Asserting query counts. They are recorded only, since phases 2–4 change them on purpose.
- G2.08 (LDAP sync, with the G-ldap group) and G2.09 (`init_roles` version bump): deferred to a follow-up story, tracked in `ADCM-8502/index.md`.

## Success signal

On current `develop`, the suite runs green twice in a row with identical goldens, and re-recording deleted goldens yields an empty `git diff`. Every scenario id in `scenarios.md` has a test, and every C/D/⚠ case is traceable to a G3 test.

## Assumptions

- The suite lives under `python/tests/cases/rbac/`, with test bundles on FS and goldens next to the tests (project test conventions).
- G3 tests assert the case-specific rows explicitly in addition to the golden diff, so each quirk can be read in the test itself.
