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

from collections import defaultdict, deque
from pathlib import Path
from typing import Generator, Type, TypeAlias
import json
import hashlib
import functools

from adcm_version import compare_prototype_versions
from core.bundle_alt.types import (
    ActionDefinition,
    BundleDefinitionKey,
    ConfigDefinition,
    Definition,
    DefinitionsMap,
    UpgradeDefinition,
)

from cm.adcm_config.config import reraise_file_errors_as_adcm_ex
from cm.models import (
    Action,
    Bundle,
    ProductCategory,
    Prototype,
    PrototypeConfig,
    PrototypeExport,
    PrototypeImport,
    SignatureStatus,
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
    prototype_dict = {}
    prototype_config_dicts = defaultdict(list)
    action_dict = defaultdict(list)
    upgrade_dict = defaultdict(list)
    prototype_import_dict = defaultdict(list)
    prototype_export_dict = defaultdict(list)

    bundle_definition = (
        bundle_definitions.get(("cluster",))
        or bundle_definitions.get(("provider",))
        or bundle_definitions.get(("adcm",))
    )

    bundle = _build_bundle(bundle_definition, bundle_hash, verification_status)

    for key, definition in bundle_definitions.items():
        _build_prototype(key, definition, prototype_dict, bundle_root)
        _build_prototype_config(key, definition.config, prototype_config_dicts)

        for action_def in definition.actions:
            action = _build_action(key, action_def, action_dict)
            _build_prototype_config(key, action_def.config, prototype_config_dicts, action)

        for upgrade_def in definition.upgrades:
            action = _build_action(key, upgrade_def.action, action_dict) if upgrade_def.action else None
            _build_upgrade(key, upgrade_def, upgrade_dict, action)
            if action:
                _build_prototype_config(key, upgrade_def.action.config, prototype_config_dicts, action)

        for definition_export in definition.exports:
            prototype_export_dict[key].append(PrototypeExport(name=definition_export))

        for definition_import in definition.imports:
            _build_stage_prototype_import(key, definition_import, prototype_import_dict)

    _save_definitions_in_db(
        bundle,
        prototype_dict,
        prototype_config_dicts,
        action_dict,
        upgrade_dict,
        prototype_import_dict,
        prototype_export_dict,
    )

    return bundle


def convert_config_definition_to_orm_model(
    definition: ConfigDefinition, action: Action | None
) -> Generator[PrototypeConfig, None, None]:
    for param_key, param_spec in definition.parameters.items():
        name = param_spec.key[0]
        subname = param_spec.name if len(param_key) != 1 else ""
        raw_default = definition.default_values.get(param_key, "")

        yield PrototypeConfig(
            action=action,
            name=name,
            subname=subname,
            type=param_spec.type,
            display_name=param_spec.display_name,
            description=param_spec.description,
            required=param_spec.required,
            limits=param_spec.limits,
            group_customization=param_spec.group_customization,
            ui_options=param_spec.ui_options,
            # should we dump all or just STACK_COMPLEX_FIELD_TYPES?
            default=json.dumps(raw_default),
        )


def _save_definitions_in_db(
    bundle: Bundle,
    prototype_dict: dict[BundleDefinitionKey, Prototype],
    prototype_config_dicts: dict[BundleDefinitionKey, list[PrototypeConfig]],
    action_dict: dict[BundleDefinitionKey, list[Action]],
    upgrade_dict: dict[BundleDefinitionKey, list[Upgrade]],
    prototype_import_dict: dict[BundleDefinitionKey, list[PrototypeImport]],
    prototype_export_dict: dict[BundleDefinitionKey, list[PrototypeExport]],
) -> None:
    _fill_bundle(prototype_dict, upgrade_dict, bundle)

    created_prototype_dict = _create_prototype_objects(prototype_dict)
    _create_prototype_depending_objects(PrototypeExport, prototype_export_dict, created_prototype_dict)
    _create_prototype_depending_objects(PrototypeImport, prototype_import_dict, created_prototype_dict)
    _create_prototype_depending_objects(Action, action_dict, created_prototype_dict)

    Upgrade.objects.bulk_create([upgrade for sublist in upgrade_dict.values() for upgrade in sublist])

    _create_prototype_config_objects(prototype_config_dicts, created_prototype_dict)


def _fill_bundle(
    prototype_dict: dict[BundleDefinitionKey, Prototype],
    upgrade_dict: dict[BundleDefinitionKey, list[Upgrade]],
    bundle: Bundle,
) -> None:
    all_upgrades = [upgrade for sublist in upgrade_dict.values() for upgrade in sublist]
    for obj in list(prototype_dict.values()) + all_upgrades:
        obj.bundle = bundle


def _create_prototype_objects(
    prototype_dict: dict[BundleDefinitionKey, Prototype],
) -> dict[BundleDefinitionKey, Prototype]:
    Prototype.objects.bulk_create(prototype_dict.values())

    for_update = deque()

    for definition_key, prototype in prototype_dict.items():
        parent_name = definition_key[1] if len(definition_key) == 3 else None
        if parent_name:
            parent_key = ("service", definition_key[1])
            prototype.parent = prototype_dict[parent_key]
            for_update.append(prototype)

    if for_update:
        Prototype.objects.bulk_update(for_update, fields=["parent"])

    return prototype_dict


def _create_prototype_depending_objects(
    obj_type: Type[PrototypeExport] | Type[PrototypeImport] | Type[Action],
    object_dict: dict[BundleDefinitionKey, list[PrototypeExport | PrototypeImport | Action]],
    prototypes_dict: dict[BundleDefinitionKey, Prototype],
) -> None:
    if not object_dict:
        return

    for definition_key, definition_data in object_dict.items():
        for definition_object in definition_data:
            definition_object.prototype = prototypes_dict[definition_key]

    obj_type.objects.bulk_create([item for sublist in object_dict.values() for item in sublist])


def _create_prototype_config_objects(
    prototype_config_dicts: dict[BundleDefinitionKey, list[PrototypeConfig]],
    created_prototype_dict: dict[BundleDefinitionKey, Prototype],
) -> None:
    for key, configs in prototype_config_dicts.items():
        for config in configs:
            if config.action:
                config.prototype = config.action.prototype
            else:
                config.prototype = created_prototype_dict[key]

    PrototypeConfig.objects.bulk_create([item for sublist in prototype_config_dicts.values() for item in sublist])


def _build_bundle(definition: Definition, bundle_hash: str, verification_status: SignatureStatus) -> Bundle:
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


def _build_prototype(
    definition_key: BundleDefinitionKey,
    definition: Definition,
    prototype_dict: dict[BundleDefinitionKey, Prototype],
    bundle_path: Path,
) -> None:
    prototype_dict[definition_key] = Prototype(
        name=definition.name,
        type=definition.type,
        version=definition.version,
        description=definition.description,
        path=definition.path,
        license=definition.license.status,
        license_path=definition.license.path,
        license_hash=_get_license_hash(bundle_path, definition.license.path),
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


def _build_action(
    definition_key: BundleDefinitionKey,
    definition: ActionDefinition,
    action_dict: dict[BundleDefinitionKey, list[Action]],
) -> Action:
    action = Action(
        name=definition.name,
        description=definition.description,
        display_name=definition.display_name,
        ui_options=definition.ui_options,
        type=definition.type,
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
    action_dict[definition_key].append(action)
    return action


def _build_stage_prototype_import(
    definition_key: BundleDefinitionKey,
    import_dict: dict,
    prototype_import_dict: dict[BundleDefinitionKey, list[PrototypeImport]],
) -> None:
    prototype_import = PrototypeImport(
        name=import_dict["name"],
        min_version=import_dict.get("min_version", ""),
        max_version=import_dict.get("max_version", ""),
        min_strict=import_dict.get("min_strict", False),
        max_strict=import_dict.get("max_strict", False),
        default=import_dict.get("default", None),
        required=import_dict.get("required", False),
        multibind=import_dict.get("multibind", False),
    )
    prototype_import_dict[definition_key].append(prototype_import)


def _build_prototype_config(
    definition_key: BundleDefinitionKey,
    definition: ConfigDefinition | None,
    prototype_config_dict: dict[BundleDefinitionKey, list[PrototypeConfig]],
    action: Action | None = None,
) -> None:
    if not definition:
        return

    prototype_config_dict[definition_key].extend(convert_config_definition_to_orm_model(definition, action))


def _build_upgrade(
    definition_key: BundleDefinitionKey,
    definition: UpgradeDefinition,
    upgrade_config_dict: dict[BundleDefinitionKey, list[Upgrade]],
    action: Action | None,
) -> None:
    upgrade = Upgrade(
        name=definition.name,
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
    upgrade_config_dict[definition_key].append(upgrade)


def _get_license_hash(bundle_path: Path, license_path: str | None) -> str | None:
    if not license_path:
        return None

    with reraise_file_errors_as_adcm_ex(filepath=license_path, reference="license file"):
        license_content = (bundle_path / license_path).read_bytes()

    return hashlib.sha256(license_content).hexdigest()
