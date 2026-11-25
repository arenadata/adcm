---
title: 'ADCM-8502 story 4: G2 RBAC change scenarios'
type: 'feature'
created: '2026-10-09'
status: 'in-review'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '5d76b17757afec0ee13eb08d8acca0a5d46c261e'
context:
  - '{project-root}/_bmad-output/specs/spec-adcm-8502-tests/SPEC.md'
  - '{project-root}/_bmad-output/specs/spec-adcm-8502-tests/scenarios.md'
  - '{project-root}/_bmad-output/specs/spec-adcm-8502-tests/conventions.md'
  - '{project-root}/_bmad-output/specs/spec-adcm-8502-tests/stories/3-g1-config-task-and-log-scenarios.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Changes to RBAC objects (policy, role, group, user membership) reach the write side and the per-user effective view unpinned: G2.01–G2.07 have no tests.

**Approach:** Add one golden-diff test per scenario variant (Design Notes) to the single suite `TestRBACWriteSide` (CAP-5), driven through the `api/v2/rbac/*` endpoints. Membership changes show up only in `auth_user_groups` and the `effective_*` tables of the diff.

## Boundaries & Constraints

**Always:** SPEC.md constraints and `conventions.md`; story 1–3 machinery as is (`self.act()`, snapshot module, missing-file recording); no DB writes outside the `act()` block; preconditions come from the shared setup. No commits; current branch.

**Never:** Production code changes. Scenarios outside G2.01–G2.07 (G2.08/G2.09 are deferred). Asserting query counts. Explicit row asserts (G3). Business-role policies through the API: the policy endpoint accepts only `role`-type roles (`PolicyCreateSerializer.validate_role`), so business roles reach G2.01 through the custom role.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Act with RBAC writes | any allowed change below | golden diff recorded / matched | AssertionError names table + rows |
| Act blocked by the API | delete role / group used in a policy (409 `ROLE_DELETE_ERROR` / `GROUP_DELETE_ERROR`) | status asserted inside the act; golden recorded as is (expected `{}`) | wrong status fails before the snapshot |
| Membership change | user/group PATCH, user create/delete | diff limited to `auth_user_groups` and `effective_*` (reviewed in the golden) | same as first row |

**Decisions:**
- G2.06 group delete is API only: `delete_group` deletes `G-idle`, `delete_group_in_policy` pins the 409 refusal (`{}`). The GOP/policy-link cascade can't be reached through the API (`api_v2/rbac/group/views.py:181`) and stays unpinned until G2.08 (user).
- Act-step shape: keep `with self.act():` (user).
- Spec kept as one story despite exceeding 1600 tokens (user).

</frozen-after-approval>

## Code Map

- `python/tests/cases/rbac/setup.py` -- `RBACWriteSideSuite.build_rbac`: groups `G-*`, users `U-*`, policies `P-*`, custom role "Custom Cluster Operator" (children: View cluster configurations, Cluster/Service Action: Common Action, View host-components; used by `P-solo-custom`). Groups and users are only accessible by name, through `Group.objects.get(display_name=...)` / `User.objects.get(username=...)` (`rbac.models`).
- `python/tests/cases/rbac/test_write_side.py` -- `TestRBACWriteSide`, sections `# G1.xx` in id order; add `# G2.xx` sections after G1.20.
- `tests/client.py:112` -- `client.v2[policy|user|role|group]` resolve to `rbac/policies|users|roles|groups/{id}`; collections via `(self.client.v2 / "rbac" / "policies")`.
- Payloads (camelCase through the client, as `api_v2/tests/test_policy.py:97`, `test_role.py:78`, `test_user.py:104`):
  - policy POST/PATCH `{"name", "role": {"id"}, "objects": [{"id", "type"}], "groups": [ids]}` (PATCH fields optional; `objects`/`groups` replace the set);
  - role POST `{"displayName", "children": [ids]}`, PATCH `{"children": [...]}` replaces the children;
  - group POST `{"displayName", "users": [ids]}`, PATCH `{"displayName"}` / `{"users": [...]}`;
  - user POST `{"username", "password", "groups": [ids]}`, PATCH `{"groups": [...]}`;
  - DELETE → 204. Role/group refusals are 409 (`cm/errors.py:191,194`).
- `rbac/services/group.py` `update` → `_update_users`: membership only, no policy apply (`01-call-sites.md` §2: group/user changes don't apply).

## Tasks & Acceptance

**Execution:**
- [x] `python/tests/cases/rbac/setup.py` -- add custom role "Custom Unused Role" (one business child, in no policy) to `build_rbac` for G2.05; update the class docstring.
- [x] `python/tests/cases/rbac/test_write_side.py` -- tests from the Design Notes table; module docstring mentions G2.
- [x] `python/tests/cases/rbac/goldens/` -- new goldens + query counts recorded; baseline re-recorded (new role rows only); no G1 golden may change.

**Acceptance Criteria:**
- Given recorded goldens, when `./run-tests.sh tests.cases.rbac` runs twice, then all tests pass and no golden changes.
- Given G2.07 goldens, when reviewed, then they contain only `auth_user_groups` and `effective_*` tables.

## Implementation Notes

**Deviations from the Code Map (code is the truth):**
- Role PATCH `children` is built from the business role names, not from `role.child`: the custom role's children also
  hold TaskRoles (D7), and `check_role_child` rejects non-business children with 400.
- "Custom Unused Role" child: `View host configurations`.

**Baseline re-recorded (review):** only `rbac_role` + `rbac_role_child` rows of "Custom Unused Role" added. No G1 golden changed.

**Recorded observations for review:** `g2_05_delete_role_in_use` and `g2_06_delete_group_in_policy` are `{}`;
`g2_02_update_policy_objects_overlap` adds A2 rows but keeps `P-overlap-edit-config` policy-GOP rows on A1;
`g2_03_delete_policy_overlapping` removes policy rows only, no `guardian_groupobjectpermission` row (G3.16 shape);
`g2_06_rename_group` re-keys GOP / policy-GOP rows only; `g2_07_remove_user_overlap` changes `auth_user_groups` only
(everything still granted through `G-solo-cluster-admin`). All G2.07 goldens hold only `auth_user_groups` / `effective_*`.

## Spec Change Log

## Review Triage Log

## Design Notes

| Test (`test_` + id) | Act |
|---|---|
| g2_01_create_policy_cluster_admin / _service_admin / _provider_admin | Cluster Administrator on A2 / Service Administrator on A2/svc_2 / Provider Administrator on P2; group `G-idle` |
| g2_01_create_policy_model_role | ADCM User, no objects, `G-idle` |
| g2_01_create_policy_custom_role | Custom Cluster Operator on A2, `G-idle` |
| g2_01_create_policy_multi_object | Cluster Administrator on A2 + B1, `G-idle` |
| g2_01_create_policy_multi_group | Cluster Administrator on A2, `G-idle` + `G-empty` |
| g2_02_update_policy_role | `P-solo-cluster-admin` role Cluster Administrator → Custom Cluster Operator (A1 tasks re-granted, J1) |
| g2_02_update_policy_objects_add / _remove | `P-solo-cluster-admin` objects A1 → A1 + A2 / `P-multi-group` objects → A1/svc_2 only |
| g2_02_update_policy_objects_overlap | `P-overlap-edit-config` objects A1 → A2 (R6: `P-overlap-admin` still grants A1) |
| g2_02_update_policy_groups_add / _remove | `P-solo-cluster-admin` + `G-idle` / `P-multi-group` → `G-multi-a` only (R8) |
| g2_03_delete_policy_overlapping | delete `P-overlap-edit-config` |
| g2_04_create_role | "G2 Role": View cluster configurations + Cluster Action: Common Action |
| g2_04_update_role_children_add / _remove | Custom Cluster Operator + Component Action: Common Action / − Cluster Action: Common Action |
| g2_05_delete_role_unused / _in_use | delete Custom Unused Role (204) / Custom Cluster Operator (409) |
| g2_06_create_group | "G-new" with U-none |
| g2_06_rename_group | `G-solo-view-host-config` → "G-renamed" (all its rows re-keyed, no apply) |
| g2_06_delete_group / _in_policy | delete `G-idle` (204) / `G-empty` (409) |
| g2_07_add_user_to_group | group PATCH: `G-solo-cluster-admin` users + U-none |
| g2_07_remove_user_overlap / _mixed / _multi | user PATCH groups: U-overlap − G-solo-view-cluster-config / U-mixed − G-cross / U-multi − G-overlap |
| g2_07_move_user_single | user PATCH: U-single G-solo-custom → G-idle (loses everything) |
| g2_07_create_user / _delete_user | POST "U-new" in G-solo-cluster-admin / DELETE U-mixed |

Membership is changed through both endpoints (group PATCH `users` once, user PATCH `groups` otherwise), since both are API paths to `auth_user_groups`.

## Verification

**Commands:**
- `./run-tests.sh tests.cases.rbac` -- first run fails "recorded" for new goldens and the baseline; second and third runs pass, goldens unchanged.
- `make pretty && make lint` -- clean.
