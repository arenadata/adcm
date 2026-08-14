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
from collections.abc import Generator, Iterable
from functools import partial
from operator import attrgetter, itemgetter
from pathlib import Path
import json
import hashlib

from core import action, bundle
from core.types import ADCMCoreType, BundleID, PrototypeID
from django.conf import settings
from django.db import IntegrityError
from pydantic import BaseModel

from cm.errors import AdcmEx
from cm.models import (
    ADCM,
    Action,
    Bundle,
    ProductCategory,
    Prototype,
    PrototypeConfig,
    PrototypeExport,
    PrototypeImport,
    SubAction,
    Upgrade,
)

# todo see if there's another place to store this
STACK_COMPLEX_FIELD_TYPES = {"json", "structure", "list", "map", "secretmap"}


class BundleRepo(bundle.BundleRepoI):
    def save_definitions(self, definitions: bundle.d.DefinitionsMap, bundle_info: bundle.BundleInfo) -> BundleID:
        bundle_definition = definitions.get(("cluster",)) or definitions.get(("provider",)) or definitions[("adcm",)]

        try:
            created_bundle = _create_bundle(
                bundle_definition,
                bundle_info.hash,
                bundle_info.signature,
                contract_version=bundle_info.contract_version,
            )
        except IntegrityError as e:
            is_constraint_violation = "duplicate key value violates unique constraint" in str(e)
            if not is_constraint_violation:
                raise

            definition = bundle_definition
            message = f'Bundle "{definition.name}" {definition.version} already installed'
            raise bundle.BundleProcessingError(message) from e

        prototypes_without_parent: dict[bundle.BundleDefinitionKey, Prototype] = {}
        prototypes_with_parent: deque[tuple[Prototype, bundle.BundleDefinitionKey]] = deque()

        configs = deque()
        actions = deque()
        sub_actions = deque()
        upgrades = deque()
        exports = deque()
        imports = deque()

        sort_by_name = partial(sorted, key=attrgetter("name"))

        for key, definition in definitions.items():
            prototype = _definition_to_model(
                definition=definition,
                bundle=created_bundle,
                license_hash=_get_license_hash(bundle_info.root, definition.license.path),
            )

            if bundle.is_component_key(key):
                # for component it's always not None, yet we need to improve it by our type system
                parent_key: bundle.BundleDefinitionKey = bundle.build_parent_key_safe(key)  # pyright: ignore[reportAssignmentType]
                prototypes_with_parent.append((prototype, parent_key))
            else:
                prototypes_without_parent[key] = prototype

            if definition.config:
                configs.extend(
                    convert_config_definition_to_orm_model(
                        definition=definition.config, prototype=prototype, action=None
                    )
                )

            for action_def in sort_by_name(definition.actions):
                action, configs_, sub_actions_ = _prepare_action_related_models(
                    definition=action_def, prototype=prototype
                )
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

                upgrade = _upgrade_definition_to_model(definition=upgrade_def, bundle=created_bundle, action=action)
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

        return created_bundle.pk

    def update_prototype_licenses(self, bundle_id: BundleID) -> None:
        Prototype.objects.filter(
            license_hash__in=Prototype.objects.filter(license="accepted").values_list("license_hash", flat=True),
            bundle_id=bundle_id,
        ).update(license="accepted")

    def recollect_categories(self) -> None:
        ProductCategory.re_collect()

    def retrieve_component_keys(self, bundle_id: BundleID) -> set[bundle.ComponentKey]:
        prototype_qs = Prototype.objects.values_list("name", "parent__name").filter(
            bundle_id=bundle_id, type=ADCMCoreType.COMPONENT
        )

        return {("component", parent_name, name) for name, parent_name in prototype_qs}

    def retrieve_versions_info(self) -> set[bundle.InstalledBundleVersion]:
        bundle_info = Bundle.objects.exclude(prototype__type=ADCMCoreType.ADCM.value).values_list(
            "name", "edition", "version", "contract_version"
        )
        return {bundle.InstalledBundleVersion(*row) for row in bundle_info}

    def retrieve_bundle_context_from_prototype(self, prototype_id: PrototypeID) -> bundle.BundleContext:
        bundle_id, hash_, contract_version = Prototype.objects.values_list(
            "bundle_id", "bundle__hash", "bundle__contract_version"
        ).get(id=prototype_id)
        path = Path(settings.BUNDLE_DIR, hash_)
        return bundle.BundleContext(id=bundle_id, root=path, contract_version=contract_version)

    def clear_old_versions_adcm_bundles(self) -> None:
        ids = (
            Prototype.objects.filter(type=ADCMCoreType.ADCM.value)
            .exclude(id=ADCM.objects.first().prototype_id)  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]
            .values_list("bundle_id", flat=True)
        )
        Bundle.objects.filter(id__in=ids).delete()


def convert_config_definition_to_orm_model(
    definition: bundle.d.ConfigDefinition, prototype: Prototype | None, action: Action | None
) -> Generator[PrototypeConfig, None, None]:
    # prototype is optional for the sake of jinja-config generation
    # should be made mandatory after its refactoring
    for param_key, param_spec in definition.parameters.items():
        root_name, *subnames = param_spec.key
        name = root_name
        subname = "/".join(subnames)

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


def _create_bundle(
    definition: bundle.d.Definition,
    bundle_hash: str,
    verification_status: bundle.SignatureStatus,
    contract_version: str,
) -> Bundle:
    return Bundle.objects.create(
        name=definition.name,
        version=definition.version,
        edition=definition.edition,
        signature_status=verification_status,
        contract_version=contract_version,
        description=definition.description,
        # version_order
        hash=bundle_hash,
        # category - on re-collect
    )


def _definition_to_model(
    definition: bundle.d.Definition,
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


def _prepare_action_related_models(
    definition: bundle.d.ActionDefinition, prototype: Prototype
) -> tuple[Action, Iterable[PrototypeConfig], Iterable[SubAction]]:
    action = _action_definition_to_model(definition=definition, prototype=prototype)

    configs = ()

    sub_actions = tuple(
        _sub_action_to_definition_to_model(definition=script, action=action) for script in definition.scripts
    )

    if definition.config:
        configs = tuple(convert_config_definition_to_orm_model(definition.config, prototype=prototype, action=action))

    return action, configs, sub_actions


def _action_definition_to_model(definition: bundle.d.ActionDefinition, prototype: Prototype) -> Action:
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
        config_template=_dump_or_none(definition.config_template),
        scripts_jinja=definition.scripts_jinja if definition.scripts_jinja else "",
        scripts_template=_dump_or_none(definition.scripts_template),
        wizard_template=_dump_or_none(definition.wizard_template),
    )


def _sub_action_to_definition_to_model(definition: action.JobSpec, action: Action) -> SubAction:
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


def _import_definition_to_model(definition: bundle.d.ImportDefinition, prototype: Prototype) -> PrototypeImport:
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


def _upgrade_definition_to_model(
    definition: bundle.d.UpgradeDefinition, bundle: Bundle, action: Action | None
) -> Upgrade:
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


# todo move to core (?)
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


def _dump_or_none(value: BaseModel | None) -> dict | None:
    return value.model_dump(mode="json") if value is not None else None
