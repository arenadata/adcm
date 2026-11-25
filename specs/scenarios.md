# Scenario catalogue

Serves CAP-4, CAP-5, CAP-6. Each scenario: shared setup → act → snapshot → compare the diff against its golden (`snapshot-format.md`). Entry ids E1–E7 and call sites: `01-call-sites.md`. C/D ids: `02-task-role.md`. Setup ids: `setup-features.md`.

Driving: API unless marked **UC** (use case / plugin executor, no real ansible).

## G1. Non-RBAC triggers (CAP-4)

| Id | Scenario | Entry | Setup |
|---|---|---|---|
| G1.01 | Create host: free / in cluster (API) | E1 | T2 R2 R5 |
| G1.02 | Create host via `adcm_add_host` (UC) | E1 | T2 R2 |
| G1.03 | Duplicate host: with / without cluster | E1 | T3 R2 |
| G1.04 | Add hosts to cluster: one / many; API + ansible (UC) | E1 | T2 R2 R5 |
| G1.05 | Remove host from cluster: API + ansible (UC) | E1 | T2 R2 J1 J2 |
| G1.06 | Add services: API, ansible service manage (UC) | E1 | B1 R2 |
| G1.07 | Delete service: API; ansible = mapping + delete (UC) | E1 keep_objects | B1 J1 J2 R2 |
| G1.08 | Create CHG; delete CHG; add/remove CHG hosts (last two: empty diff expected) | E1 / none | T4 R2 |
| G1.09 | Change HC mapping (add, remove, move): API, ansible `hc`, task hc_acl, finalizer (UC) | E2 mapping | T2 R2 R7 J2 |
| G1.10 | Plain upgrade: cluster / provider | E2 upgrade | B3 B4 R2 R7 |
| G1.11 | Upgrade through action with `bundle_switch` / `bundle_revert` (UC) | E2 + E4 | B3 J1 R2 |
| G1.12 | Save config: object / CHG (API), from job / `adcm_config` plugin (UC) | E3 | T4 T6 R2 |
| G1.13 | Launch task on each target type | E4 | J1 R2 R5 |
| G1.14 | Launch host action / AHG task / ADCM task | E4 | J2 J3 J4 R2 |
| G1.15 | Wizard step launching a task | E4 | J1 R2 |
| G1.16 | Custom log / check log during a run (UC) | E5 | J5 R5 |
| G1.17 | Upload bundle; delete bundle | E6 | B5 R2 |
| G1.18 | Delete cluster / provider / host (no RBAC write expected; stale GOPs) | none | T1 T2 R2 |
| G1.19 | Logrotate | none | J7 |
| G1.20 | Cluster import (`load`) | E1 × N | B1 B4 R2 |

## G2. RBAC changes (CAP-5)

G2.08 (LDAP sync) and G2.09 (`init_roles` version bump) are deferred: see `ADCM-8502/03-equivalence-suite.md` §3.

| Id | Scenario | Setup |
|---|---|---|
| G2.01 | Create policy: each role kind, single/multi object, single/multi group | R2 R3 R4 R7 R8 |
| G2.02 | Update policy: change role / objects / groups (add, remove) | R2 R6 R8 J1 |
| G2.03 | Delete policy with an overlapping policy present | R6 |
| G2.04 | Create custom role; update its children (add/remove business roles) | R4 J1 |
| G2.05 | Delete role: allowed when unused, blocked when in use | R4 |
| G2.06 | Group create / rename / delete (cascade of GOPs and policy links) | R1 R8 |
| G2.07 | User add to / remove from group (U-overlap, U-mixed, U-multi, U-single, U-none); user create/delete. Write-side tables unchanged; the effective view changes by exactly the grants no other group of the user still provides | R1 |

## G3. Corner cases: confirm current behaviour (CAP-6)

The mark is `preserve` or `intentional change`. It stays unset in this story and is decided before Phase 2+.

| Id | Case | Source | Setup | Mark |
|---|---|---|---|---|
| G3.01 | Launch-time qualification: `view_action` through this policy + `view_owner` through any policy | C1 | J1 R1 R6 | |
| G3.02 | Grant goes to all groups of a qualifying policy | C2 | R8 J1 | |
| G3.03 | Policy created after the task sees it only if the shared role already holds the TaskRole | C3 | J6 R5 | |
| G3.04 | Re-apply grants task perms without action/owner check | C4 | J1 R5 | |
| G3.05 | Group added to a policy later gets past tasks | C5 | J1 R8 | |
| G3.06 | Task visibility lost after unmap / host removal / service delete; one-shot `keep_objects`, then the next re-apply | C6 D3 | J1 J2 T2 | |
| G3.07 | Custom log granted across objects to every policy with the same role | C7 D2 | J5 R5 | |
| G3.08 | Custom role edit wipes task visibility; spec upgrade keeps it | C8 D5 | R4 J1 | |
| G3.09 | AHG task perms disappear after the first re-apply | D1 | J3 R2 | |
| G3.10 | Unattached / rotated TaskRoles stay | D4 D6 | J6 J7 | |
| G3.11 | TaskRole widens the custom role traversal (no permission effect expected) | D7 | R4 J2 | |
| G3.12 | Duplicate host without cluster not covered by provider policies | 01 §2.1 ⚠ | T3 R2 | |
| G3.13 | Component-scoped policy not refreshed on mapping change | 01 §2.1 ⚠ | T2 R2 | |
| G3.14 | Stale GOPs after object deletion | 01 §2.1 ⚠ | T1 R2 | |
| G3.15 | Multi-object policy re-applied several times in one operation (state equal, count differs) | 01 §3 | R7 | |
| G3.16 | Overlapping policies: removing one keeps the shared GOP for the other | — | R6 | |
| G3.17 | ActionRole for a deleted action (bundle deleted while a policy uses it) | preload risk 2 | B5 R2 | |

C9 (ADCM-owned tasks get no E4 grant) is covered by G1.14's ADCM task.
