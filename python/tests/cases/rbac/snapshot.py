# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Id-independent snapshot of the RBAC write side.

Write-side tables are read directly, every DB id is replaced by a natural key (`type:key`),
and a per-user effective view is derived from the same rows.
Rows referencing deleted objects are kept as `<dangling:type:old-key>`.
"""

from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, NamedTuple, TypeAlias
from unittest import TestCase

from cm.models import (
    ADCM,
    Action,
    ActionHostGroup,
    Cluster,
    Component,
    ConfigHostGroup,
    ConfigLog,
    Host,
    JobLog,
    LogStorage,
    Prototype,
    Provider,
    Service,
    TaskLog,
)
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User as AuthUser
from django.contrib.contenttypes.models import ContentType
from guardian.models import GroupObjectPermission
from rbac.models import Group, Policy, PolicyObject, PolicyPermission, Role
import yaml

ROW_SEPARATOR: Final = " | "

# model name (as in `ContentType.model`) -> prefix of the object key
KEY_PREFIXES: Final[dict[str, str]] = {
    "adcm": "adcm",
    "cluster": "cluster",
    "service": "service",
    "component": "component",
    "provider": "provider",
    "host": "host",
    "confighostgroup": "chg",
    "actionhostgroup": "ahg",
    "objectconfig": "config",
    "configlog": "configlog",
    "prototype": "prototype",
    "action": "action",
    "tasklog": "task",
    "joblog": "job",
    "logstorage": "log",
}

TABLES: Final = (
    "guardian_groupobjectpermission",
    "rbac_policy_group_object_perm",
    "auth_group_permissions",
    "rbac_policypermission",
    "rbac_role",
    "rbac_role_child",
    "rbac_policy_object",
    "auth_user_groups",
    "effective_object_perm",
    "effective_model_perm",
)

NO_POLICY: Final = "<no policy>"
NO_OWNER: Final = "<no owner>"
TASK_ROLE_PREFIX: Final = "task-role:"


class ObjectRef(NamedTuple):
    model: str
    pk: int


# object -> key body (without `type:` prefix)
ObjectKeys: TypeAlias = dict[ObjectRef, str]
Row: TypeAlias = tuple[str, ...]
BaselineData: TypeAlias = dict[str, list[str]]
DiffData: TypeAlias = dict[str, dict[str, list[str]]]


@dataclass(frozen=True, slots=True)
class Snapshot:
    """Rows of every compared table (and the effective view) as sorted natural-key tuples"""

    tables: dict[str, tuple[Row, ...]]

    def serialize(self) -> BaselineData:
        return {table: [ROW_SEPARATOR.join(row) for row in rows] for table, rows in self.tables.items()}

    def row_counts(self) -> dict[str, int]:
        return {table: len(rows) for table, rows in self.tables.items()}


class QueryCounter:
    """
    Wrapper for `connection.execute_wrapper` counting executed queries.

    `CaptureQueriesContext` isn't used: it keeps only the last 9000 queries.
    """

    def __init__(self) -> None:
        self.count = 0

    def __call__(self, execute: Callable[..., Any], sql: str, params: Any, many: bool, context: dict) -> Any:
        self.count += 1
        return execute(sql, params, many, context)


def collect_object_keys() -> ObjectKeys:
    """Natural key body of every existing object that may be referenced from the write-side tables"""

    keys: ObjectKeys = {}
    content_type_models = dict(ContentType.objects.values_list("id", "model"))

    def full_key(ref: ObjectRef) -> str:
        if ref not in keys:
            return NO_OWNER

        return f"{KEY_PREFIXES[ref.model]}:{keys[ref]}"

    for model, model_name in ((ADCM, "adcm"), (Cluster, "cluster"), (Provider, "provider")):
        keys |= {ObjectRef(model_name, pk): name for pk, name in model.objects.values_list("id", "name")}

    keys |= {
        ObjectRef("service", pk): f"{cluster}/{service}"
        for pk, cluster, service in Service.objects.values_list("id", "cluster__name", "prototype__name")
    }
    keys |= {
        ObjectRef("component", pk): f"{cluster}/{service}/{component}"
        for pk, cluster, service, component in Component.objects.values_list(
            "id", "cluster__name", "service__prototype__name", "prototype__name"
        )
    }

    duplicate_ranks: Counter[int] = Counter()
    for pk, fqdn, original_id in Host.objects.order_by("id").values_list("id", "fqdn", "original_id"):
        if original_id is None:
            keys[ObjectRef("host", pk)] = fqdn
        else:
            duplicate_ranks[original_id] += 1
            keys[ObjectRef("host", pk)] = f"{fqdn}~dup#{duplicate_ranks[original_id]}"

    for model, model_name in ((ConfigHostGroup, "confighostgroup"), (ActionHostGroup, "actionhostgroup")):
        keys |= {
            ObjectRef(model_name, pk): f"{full_key(ObjectRef(content_type_models[type_id], object_id))}/{name}"
            for pk, type_id, object_id, name in model.objects.values_list("id", "object_type_id", "object_id", "name")
        }

    for model, model_name in (
        (ADCM, "adcm"),
        (Cluster, "cluster"),
        (Service, "service"),
        (Component, "component"),
        (Provider, "provider"),
        (Host, "host"),
        (ConfigHostGroup, "confighostgroup"),
    ):
        keys |= {
            ObjectRef("objectconfig", config_id): full_key(ObjectRef(model_name, pk))
            for pk, config_id in model.objects.filter(config__isnull=False).values_list("id", "config_id")
        }

    revisions: Counter[int] = Counter()
    for pk, config_id in ConfigLog.objects.order_by("id").values_list("id", "obj_ref_id"):
        revisions[config_id] += 1
        keys[ObjectRef("configlog", pk)] = (
            f"{keys.get(ObjectRef('objectconfig', config_id), NO_OWNER)}@rev{revisions[config_id]}"
        )

    for pk, bundle, version, type_, parent, name in Prototype.objects.values_list(
        "id", "bundle__name", "bundle__version", "type", "parent__name", "name"
    ):
        path = f"{parent}/{name}" if parent else name
        keys[ObjectRef("prototype", pk)] = f"{bundle}-{version}/{type_}/{path}"

    keys |= {
        ObjectRef("action", pk): f"{keys[ObjectRef('prototype', prototype_id)]}:{name}"
        for pk, prototype_id, name in Action.objects.values_list("id", "prototype_id", "name")
    }

    launches: Counter[tuple[str, str]] = Counter()
    for pk, type_id, object_id, name in TaskLog.objects.order_by("id").values_list(
        "id", "object_type_id", "object_id", "name"
    ):
        target = full_key(ObjectRef(content_type_models.get(type_id, ""), object_id))
        launches[target, name] += 1
        keys[ObjectRef("tasklog", pk)] = f"{target}:{name}#{launches[target, name]}"

    job_orders: Counter[int | None] = Counter()
    for pk, task_id in JobLog.objects.order_by("id").values_list("id", "task_id"):
        job_orders[task_id] += 1
        task = keys[ObjectRef("tasklog", task_id)] if task_id is not None else NO_OWNER
        keys[ObjectRef("joblog", pk)] = f"{task}/{job_orders[task_id]}"

    keys |= {
        ObjectRef("logstorage", pk): f"{keys[ObjectRef('joblog', job_id)]}/{name}:{type_}"
        for pk, job_id, name, type_ in LogStorage.objects.values_list("id", "job_id", "name", "type")
    }

    _ensure_unique(keys)

    return keys


def take_snapshot(key_map: ObjectKeys) -> Snapshot:
    """
    Read the write side and replace ids with natural keys.

    Objects that don't exist any more are rendered as `<dangling:type:key>`,
    `key` is taken from `key_map` (keys collected before the objects were deleted),
    otherwise it's `#n`: rank of the old pk among unresolved pks of the same type.
    """

    raw_tables = _collect_raw_tables()
    current_keys = collect_object_keys()
    dangling = _build_dangling_keys(raw_tables=raw_tables, current_keys=current_keys, key_map=key_map)

    def render(cell: "_Cell") -> str:
        match cell:
            case str():
                return cell
            case _Prefixed(prefix=prefix, ref=ref):
                return f"{prefix}{render(ref)}"
            case ObjectRef() if cell in current_keys:
                return f"{KEY_PREFIXES[cell.model]}:{current_keys[cell]}"
            case ObjectRef():
                return dangling[cell]

    return Snapshot(
        tables={
            table: tuple(sorted(tuple(render(cell) for cell in row) for row in raw_tables[table])) for table in TABLES
        }
    )


def diff(before: Snapshot, after: Snapshot) -> DiffData:
    """Per-table rows added/removed between two snapshots, only tables that changed are present"""

    result: DiffData = {}

    for table in TABLES:
        before_rows = Counter(before.tables.get(table, ()))
        after_rows = Counter(after.tables.get(table, ()))
        added = sorted((after_rows - before_rows).elements())
        removed = sorted((before_rows - after_rows).elements())

        if added or removed:
            result[table] = {
                "added": [ROW_SEPARATOR.join(row) for row in added],
                "removed": [ROW_SEPARATOR.join(row) for row in removed],
            }

    return result


def assert_matches_golden(case: TestCase, path: Path, actual: BaselineData | DiffData) -> None:
    """
    Compare `actual` with the golden file table by table.

    Missing golden is recorded from `actual` and the test fails: the recorded file has to be reviewed.
    """

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_dump_yaml(actual))
        case.fail(f"Golden {path.name} was missing: recorded from the current output, review it")

    expected = yaml.safe_load(path.read_text()) or {}
    mismatches = _find_mismatches(expected=_flatten_sections(expected), actual=_flatten_sections(actual))

    if mismatches:
        case.fail(f"Snapshot differs from golden {path.name}:\n" + "\n".join(mismatches))


def record_query_count(path: Path, scenario: str, count: int) -> None:
    """Record query count of the scenario's act step, file is never compared"""

    counts: dict[str, int] = {}
    if path.exists():
        counts = yaml.safe_load(path.read_text()) or {}

    counts[scenario] = count

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump_yaml(dict(sorted(counts.items()))))


# Protected


class _Prefixed(NamedTuple):
    prefix: str
    ref: ObjectRef


_Cell: TypeAlias = str | ObjectRef | _Prefixed
_RawRow: TypeAlias = tuple[_Cell, ...]


def _collect_raw_tables() -> dict[str, list[_RawRow]]:
    content_types = {pk: (app, model) for pk, app, model in ContentType.objects.values_list("id", "app_label", "model")}
    permissions = {
        pk: f"{app}.{codename}"
        for pk, app, codename in Permission.objects.values_list("id", "content_type__app_label", "codename")
    }
    group_names = dict(AuthGroup.objects.values_list("id", "name"))
    group_names |= {pk: name for pk, name in Group.objects.values_list("pk", "display_name") if name}
    user_names = dict(AuthUser.objects.values_list("id", "username"))
    policy_names = dict(Policy.objects.values_list("id", "name"))

    def object_ref(content_type_id: int, object_pk: str | int) -> ObjectRef:
        app, model = content_types[content_type_id]
        if model not in KEY_PREFIXES:
            message = f"Snapshot has no natural key rule for model `{app}.{model}`"
            raise RuntimeError(message)

        return ObjectRef(model, int(object_pk))

    role_keys: dict[int, str | _Prefixed] = {}
    role_rows: list[_RawRow] = []
    for pk, name, type_, class_name, init_params in Role.objects.values_list(
        "id", "name", "type", "class_name", "init_params"
    ):
        key = name
        if class_name == "TaskRole":
            key = _Prefixed(prefix=TASK_ROLE_PREFIX, ref=ObjectRef("tasklog", int(init_params["task_id"])))

        role_keys[pk] = key
        role_rows.append((key, type_))

    gops = {
        pk: (group_names[group_id], permissions[permission_id], object_ref(type_id, object_pk))
        for pk, group_id, permission_id, type_id, object_pk in GroupObjectPermission.objects.values_list(
            "id", "group_id", "permission_id", "content_type_id", "object_pk"
        )
    }

    policy_objects = {
        pk: object_ref(type_id, object_id)
        for pk, type_id, object_id in PolicyObject.objects.values_list("id", "content_type_id", "object_id")
    }

    model_perm_policies: defaultdict[int, list[str]] = defaultdict(list)
    for policy_id, policy_permission_id in Policy.model_perm.through.objects.values_list(
        "policy_id", "policypermission_id"
    ):
        model_perm_policies[policy_permission_id].append(policy_names[policy_id])

    policy_permission_rows: list[_RawRow] = []
    for pk, user_id, group_id, permission_id in PolicyPermission.objects.values_list(
        "id", "user_id", "group_id", "permission_id"
    ):
        holder = "-"
        if group_id is not None:
            holder = f"group:{group_names[group_id]}"
        elif user_id is not None:
            holder = f"user:{user_names[user_id]}"

        permission = permissions[permission_id] if permission_id is not None else "-"
        policy_permission_rows.extend(
            (policy, holder, permission) for policy in model_perm_policies.get(pk, [NO_POLICY])
        )

    group_permissions: defaultdict[int, set[str]] = defaultdict(set)
    for group_id, permission_id in AuthGroup.permissions.through.objects.values_list("group_id", "permission_id"):
        group_permissions[group_id].add(permissions[permission_id])

    group_object_permissions: defaultdict[str, set[tuple[str, ObjectRef]]] = defaultdict(set)
    for group, permission, ref in gops.values():
        group_object_permissions[group].add((permission, ref))

    user_groups = list(AuthUser.groups.through.objects.values_list("user_id", "group_id"))

    effective_objects: set[_RawRow] = set()
    effective_models: set[_RawRow] = set()
    for user_id, group_id in user_groups:
        user = user_names[user_id]
        effective_objects |= {
            (user, permission, ref) for permission, ref in group_object_permissions[group_names[group_id]]
        }
        effective_models |= {(user, permission) for permission in group_permissions[group_id]}

    return {
        "guardian_groupobjectpermission": list(gops.values()),
        "rbac_policy_group_object_perm": [
            (policy_names[policy_id], *gops[gop_id])
            for policy_id, gop_id in Policy.group_object_perm.through.objects.values_list(
                "policy_id", "groupobjectpermission_id"
            )
        ],
        "auth_group_permissions": [
            (group_names[group_id], permission)
            for group_id, group_perms in group_permissions.items()
            for permission in group_perms
        ],
        "rbac_policypermission": policy_permission_rows,
        "rbac_role": role_rows,
        "rbac_role_child": [
            (role_keys[from_id], role_keys[to_id])
            for from_id, to_id in Role.child.through.objects.values_list("from_role_id", "to_role_id")
        ],
        "rbac_policy_object": [
            (policy_names[policy_id], policy_objects[policy_object_id])
            for policy_id, policy_object_id in Policy.object.through.objects.values_list("policy_id", "policyobject_id")
        ],
        "auth_user_groups": [(user_names[user_id], group_names[group_id]) for user_id, group_id in user_groups],
        "effective_object_perm": list(effective_objects),
        "effective_model_perm": list(effective_models),
    }


def _build_dangling_keys(
    raw_tables: Mapping[str, Iterable[_RawRow]], current_keys: ObjectKeys, key_map: ObjectKeys
) -> dict[ObjectRef, str]:
    unresolved: defaultdict[str, set[int]] = defaultdict(set)
    known: dict[ObjectRef, str] = {}

    for rows in raw_tables.values():
        for row in rows:
            for cell in row:
                ref = cell.ref if isinstance(cell, _Prefixed) else cell
                if not isinstance(ref, ObjectRef) or ref in current_keys:
                    continue

                if ref in key_map:
                    known[ref] = key_map[ref]
                else:
                    unresolved[ref.model].add(ref.pk)

    for model, pks in unresolved.items():
        known |= {ObjectRef(model, pk): f"#{rank}" for rank, pk in enumerate(sorted(pks), start=1)}

    return {ref: f"<dangling:{ref.model}:{key}>" for ref, key in known.items()}


def _ensure_unique(keys: ObjectKeys) -> None:
    seen: set[tuple[str, str]] = set()
    for ref, key in keys.items():
        if (ref.model, key) in seen:
            message = f"Natural key `{key}` of {ref.model} is not unique"
            raise RuntimeError(message)

        seen.add((ref.model, key))


def _flatten_sections(data: Mapping) -> dict[str, list[str]]:
    flat: dict[str, list[str]] = {}

    for table, content in data.items():
        if isinstance(content, Mapping):
            flat |= {f"{table} ({section})": list(rows or ()) for section, rows in content.items()}
        else:
            flat[table] = list(content or ())

    return flat


def _find_mismatches(expected: dict[str, list[str]], actual: dict[str, list[str]]) -> list[str]:
    mismatches = []

    for section in sorted(expected.keys() | actual.keys()):
        expected_rows = Counter(expected.get(section, ()))
        actual_rows = Counter(actual.get(section, ()))

        missing = sorted((expected_rows - actual_rows).elements())
        unexpected = sorted((actual_rows - expected_rows).elements())

        if missing or unexpected:
            mismatches.append(f"table {section}:")
            mismatches.extend(f"  - {row}  (in golden, not in actual)" for row in missing)
            mismatches.extend(f"  + {row}  (in actual, not in golden)" for row in unexpected)

    return mismatches


def _dump_yaml(data: Mapping) -> str:
    return yaml.safe_dump(dict(data), sort_keys=False, allow_unicode=True, width=10_000, default_flow_style=False)
