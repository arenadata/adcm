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

from collections import deque
from operator import attrgetter, itemgetter
from pathlib import Path
from typing import Generator, Iterable, TypeAlias
import json
import hashlib
import functools

from adcm_version import compare_prototype_versions
from core.bundle_alt._config import STACK_COMPLEX_FIELD_TYPES
from core.bundle_alt.errors import BundleProcessingError
from core.bundle_alt.predicates import is_component_key
from core.bundle_alt.representation import build_parent_key_safe
from core.bundle_alt.types import (
    ActionDefinition,
    BundleDefinitionKey,
    ConfigDefinition,
    Definition,
    DefinitionsMap,
    ImportDefinition,
    UpgradeDefinition,
)
from core.job.types import JobSpec
from django.db import IntegrityError

from cm.errors import AdcmEx
from cm.models import (
    Action,
    Bundle,
    ProductCategory,
    Prototype,
    PrototypeConfig,
    PrototypeExport,
    PrototypeImport,
    SignatureStatus,
    SubAction,
    Upgrade,
)


def find_bundle_by_hash(hash_: str) -> Bundle | None:
    return Bundle.objects.filter(hash=hash_).first()


def order_versions():
    # COPIED FROM cm.bundle
    _order_model_versions(Prototype)
    _order_model_versions(Bundle)


def _order_model_versions(model):
    # COPIED FROM cm.bundle
    items = []
    for obj in model.objects.order_by("id"):
        items.append(obj)
    ver = ""
    count = 0
    for obj in sorted(
        items,
        key=functools.cmp_to_key(lambda obj1, obj2: compare_prototype_versions(obj1.version, obj2.version)),
    ):
        if ver != obj.version:
            count += 1
        obj.version_order = count
        ver = obj.version
    # Update all table in one time. That is much faster than one by one method
    model.objects.bulk_update(items, fields=["version_order"])


def recollect_categories():
    ProductCategory.re_collect()


# save bundle


PrototypeParentName: TypeAlias = str | None


def save_definitions(
    bundle_definitions: DefinitionsMap, bundle_root: Path, bundle_hash: str, verification_status: SignatureStatus
) -> Bundle:
    bundle_definition = (
        bundle_definitions.get(("cluster",)) or bundle_definitions.get(("provider",)) or bundle_definitions[("adcm",)]
    )

    try:
        bundle = _create_bundle(bundle_definition, bundle_hash, verification_status)
    except IntegrityError as e:
        is_constraint_violation = "duplicate key value violates unique constraint" in str(e)
        if not is_constraint_violation:
            raise

        definition = bundle_definition
        message = f'Bundle "{definition.name}" {definition.version} already installed'
        raise BundleProcessingError(message) from e

    prototypes_without_parent: dict[BundleDefinitionKey, Prototype] = {}
    prototypes_with_parent: deque[tuple[Prototype, BundleDefinitionKey]] = deque()

    configs = deque()
    actions = deque()
    sub_actions = deque()
    upgrades = deque()
    exports = deque()
    imports = deque()

    sort_by_name = functools.partial(sorted, key=attrgetter("name"))

    for key, definition in bundle_definitions.items():
        prototype = _definition_to_model(
            definition=definition, bundle=bundle, license_hash=_get_license_hash(bundle_root, definition.license.path)
        )

        if is_component_key(key):
            parent_key = build_parent_key_safe(key)
            prototypes_with_parent.append((prototype, parent_key))
        else:
            prototypes_without_parent[key] = prototype

        if definition.config:
            configs.extend(
                convert_config_definition_to_orm_model(definition=definition.config, prototype=prototype, action=None)
            )

        for action_def in sort_by_name(definition.actions):
            action, configs_, sub_actions_ = _prepare_action_related_models(definition=action_def, prototype=prototype)
            actions.append(action)
            sub_actions.extend(sub_actions_)
            configs.extend(configs_)

        for upgrade_def in definition.upgrades:
            action = None
            if upgrade_def.action:
                action, configs_, sub_actions_ = _prepare_action_related_models(
                    definition=upgrade_def.action, prototype=prototype
                )
                actions.append(action)
                sub_actions.extend(sub_actions_)
                configs.extend(configs_)

            upgrade = _upgrade_definition_to_model(definition=upgrade_def, bundle=bundle, action=action)
            upgrades.append(upgrade)

        exports.extend(PrototypeExport(name=export, prototype=prototype) for export in definition.exports)

        imports.extend(
            _import_definition_to_model(definition=import_, prototype=prototype) for import_ in definition.imports
        )

    Prototype.objects.bulk_create(objs=prototypes_without_parent.values())

    for proto, parent_key in prototypes_with_parent:
        proto.parent = prototypes_without_parent[parent_key]

    Prototype.objects.bulk_create(objs=map(itemgetter(0), prototypes_with_parent))
    Action.objects.bulk_create(objs=actions)
    SubAction.objects.bulk_create(objs=sub_actions)
    Upgrade.objects.bulk_create(objs=upgrades)
    PrototypeConfig.objects.bulk_create(objs=configs)
    PrototypeImport.objects.bulk_create(objs=imports)
    PrototypeExport.objects.bulk_create(objs=exports)

    return bundle


def convert_config_definition_to_orm_model(
    definition: ConfigDefinition, prototype: Prototype | None, action: Action | None
) -> Generator[PrototypeConfig, None, None]:
    # prototype is optional for the sake of jinja-config generation
    # should be made mandatory after its refactoring
    for param_key, param_spec in definition.parameters.items():
        name = param_spec.key[0]
        subname = param_spec.name if len(param_key) != 1 else ""

        default = ""
        if (value := definition.default_values.get(param_key, None)) is not None:
            default = value

            if param_spec.type in STACK_COMPLEX_FIELD_TYPES:
                default = json.dumps(default)

        yield PrototypeConfig(
            action=action,
            prototype=prototype,
            name=name,
            subname=subname,
            type=param_spec.type,
            display_name=param_spec.display_name,
            description=param_spec.description,
            required=param_spec.required,
            limits=param_spec.limits,
            group_customization=param_spec.group_customization,
            ui_options=param_spec.ui_options,
            default=default,
            ansible_options=param_spec.ansible_options,
        )


def _prepare_action_related_models(
    definition: ActionDefinition, prototype: Prototype
) -> tuple[Action, Iterable[PrototypeConfig], Iterable[SubAction]]:
    action = _action_definition_to_model(definition=definition, prototype=prototype)

    configs = ()

    sub_actions = tuple(
        _sub_action_to_definition_to_model(definition=script, action=action) for script in definition.scripts
    )

    if definition.config:
        configs = tuple(convert_config_definition_to_orm_model(definition.config, prototype=prototype, action=action))

    return action, configs, sub_actions


def _create_bundle(definition: Definition, bundle_hash: str, verification_status: SignatureStatus) -> Bundle:
    return Bundle.objects.create(
        name=definition.name,
        version=definition.version,
        edition=definition.edition,
        signature_status=verification_status,
        description=definition.description,
        # version_order
        hash=bundle_hash,
        # category - on re-collect
    )


def _definition_to_model(
    definition: Definition,
    bundle: Bundle,
    license_hash: str | None,
) -> Prototype:
    return Prototype(
        bundle=bundle,
        name=definition.name,
        type=definition.type,
        version=definition.version,
        description=definition.description,
        path=definition.path,
        license=definition.license.status,
        license_path=definition.license.path,
        license_hash=license_hash,
        display_name=definition.display_name,
        required=definition.required,
        shared=definition.shared,
        config_group_customization=definition.config_group_customization,
        flag_autogeneration=definition.flag_autogeneration,
        adcm_min_version=definition.adcm_min_version,
        venv=definition.venv,
        monitoring=definition.monitoring,
        allow_maintenance_mode=definition.allow_maintenance_mode,
        constraint=definition.constraint,
        bound_to=definition.bound_to,
        requires=definition.requires,
    )


def _action_definition_to_model(definition: ActionDefinition, prototype: Prototype) -> Action:
    return Action(
        name=definition.name,
        prototype=prototype,
        description=definition.description,
        display_name=definition.display_name,
        ui_options=definition.ui_options,
        type=definition.type,
        venv=definition.venv,
        state_available=definition.available_at.states,
        state_unavailable=definition.unavailable_at.states,
        state_on_success=definition.on_success.set_state if definition.on_success.set_state else "",
        state_on_fail=definition.on_fail.set_state if definition.on_fail.set_state else "",
        multi_state_available=definition.available_at.multi_states,
        multi_state_unavailable=definition.unavailable_at.multi_states,
        multi_state_on_success_set=definition.on_success.set_multi_state,
        multi_state_on_success_unset=definition.on_success.unset_multi_state,
        multi_state_on_fail_set=definition.on_fail.set_multi_state,
        multi_state_on_fail_unset=definition.on_fail.unset_multi_state,
        hostcomponentmap=definition.hostcomponentmap,
        host_action=definition.is_host_action,
        allow_to_terminate=definition.allow_to_terminate,
        partial_execution=definition.partial_execution,
        allow_for_action_host_group=definition.allow_for_action_host_group,
        allow_in_maintenance_mode=definition.allow_in_maintenance_mode,
        config_jinja=definition.config_jinja,
        scripts_jinja=definition.scripts_jinja if definition.scripts_jinja else "",
    )


def _sub_action_to_definition_to_model(definition: JobSpec, action: Action) -> SubAction:
    return SubAction(
        action=action,
        name=definition.name,
        display_name=definition.display_name,
        script=definition.script,
        script_type=definition.script_type.value,
        state_on_fail=definition.state_on_fail,
        multi_state_on_fail_set=definition.multi_state_on_fail_set,
        multi_state_on_fail_unset=definition.multi_state_on_fail_unset,
        params=definition.params,
        allow_to_terminate=definition.allow_to_terminate,
    )


def _import_definition_to_model(definition: ImportDefinition, prototype: Prototype) -> None:
    return PrototypeImport(
        name=definition.name,
        prototype=prototype,
        min_version=definition.min_version.value,
        max_version=definition.max_version.value,
        min_strict=definition.min_version.is_strict,
        max_strict=definition.max_version.is_strict,
        default=definition.default,
        required=definition.is_required,
        multibind=definition.is_multibind_allowed,
    )


def _upgrade_definition_to_model(definition: UpgradeDefinition, bundle: Bundle, action: Action | None) -> None:
    return Upgrade(
        name=definition.name,
        bundle=bundle,
        action=action,
        display_name=definition.display_name,
        description=definition.description,
        min_version=definition.restrictions.min_version.value,
        max_version=definition.restrictions.max_version.value,
        max_strict=definition.restrictions.max_version.is_strict,
        min_strict=definition.restrictions.min_version.is_strict,
        from_edition=definition.restrictions.from_editions,
        state_available=definition.state_available,
        state_on_success=definition.state_on_success,
    )


def _get_license_hash(bundle_path: Path, license_path: str | None) -> str | None:
    if not license_path:
        return None

    try:
        license_content = (bundle_path / license_path).read_bytes()
    except FileNotFoundError as err:
        msg = f'"{license_path}" is not found (license file)'
        raise AdcmEx(code="CONFIG_TYPE_ERROR", msg=msg) from err
    except PermissionError as err:
        msg = f'"{license_path}" can not be open (license file)'
        raise AdcmEx(code="CONFIG_TYPE_ERROR", msg=msg) from err

    return hashlib.sha256(license_content).hexdigest()
