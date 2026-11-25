# Snapshot format

Serves CAP-1, CAP-2, CAP-7.

## Compared tables

| Table | Row → natural key |
|---|---|
| `guardian_groupobjectpermission` | (group name, `app.codename`, object key) |
| `rbac_policy_group_object_perm` | (policy name, GOP key) |
| `auth_group_permissions` | (group name, `app.codename`) |
| `rbac_policypermission` + `rbac_policy_model_perm` | (policy name, group/user name, `app.codename`) |
| `rbac_role` + `rbac_role_child` | (role name, child role name). TaskRole → task key |
| `rbac_policy_object` | (policy name, object key) |
| `auth_user_groups` | (user name, group name) |

GOP = one `guardian_groupobjectpermission` row. Write side is group-only: there are no `UserObjectPermission` writes, `Policy` has no users, and `PolicyPermission.user` is never set.

## Derived effective view (per user)

The union of the grants of all the user's groups: `(user, app.codename, object key)` plus model perms. It is computed in test code from the tables above. Membership changes leave the write-side tables untouched and show up only here.

## Object keys

| Object | Key |
|---|---|
| cluster, provider | name |
| service, component | path `cluster/service/component` |
| host | fqdn |
| CHG, AHG | owner key + group name |
| ConfigLog | owner key + revision number within owner |
| Action | prototype key + action name |
| Task | target key + action name + launch order |
| Job | task key + job order |
| Log | job key + (name, type) |
| deleted object | `<dangling:type:old-key>` when resolvable. Stale rows must stay visible |

## Golden layout

- **Baseline:** full snapshot (all tables + effective view) taken right after the shared setup. One file per suite.
- **Per scenario:** diff baseline → after-act snapshot, per table. Rows `added` / `removed`, sorted by natural key. An empty diff is recorded explicitly (e.g. G1.08 CHG host changes, G1.18 deletes).
- Comparison: the actual baseline equals the golden baseline. The actual per-scenario diff equals the golden diff.
- Recording: when a golden file is missing, the test writes it from the current output and fails with "recorded, review it". To update a golden, delete the file and rerun. There is no regeneration flag. Golden changes are reviewed like code.
- Query count of the act step is recorded per scenario, in one separate file per suite (not a golden, never compared).
