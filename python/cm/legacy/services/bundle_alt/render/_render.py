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

from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TypeVar

from core.action import JobSpec
from core.legacy.bundle_alt.process import (
    ConfigConversionContext,
    ScriptsConversionContext,
    parse_action_process_stages,
    parse_scripts,
)
from core.legacy.bundle_alt.schema import ActionProcessStage, DynamicScriptsSchema, WizardScriptsSchema
from core.legacy.bundle_alt.validation import check_action_hc_acl_rules
from core.templates import RendererEnv, Template, get_renderer
from core.types import ClusterID
import core

from cm.legacy.services.action_process import repo
from cm.legacy.services.bundle_alt.errors import convert_bundle_errors_to_adcm_ex
from cm.legacy.services.bundle_alt.load import parse_config_jinja
from cm.legacy.services.bundle_alt.render._context import ActionArgs, ContextGatherer, TaskArgs
from cm.legacy.utils import decrypt_secrets
from cm.models import ActionHostGroup, Cluster, Component, Host, PrototypeConfig, Service


@dataclass(slots=True)
class Environment:
    bundle_root: Path


# Render by Target


@convert_bundle_errors_to_adcm_ex
def render_process(
    template: Template,
    environment: Environment,
    context_args: ActionArgs,
    context_gatherer: ContextGatherer,
) -> list[ActionProcessStage]:
    raw = _render_template(
        template=template,
        environment=environment,
        build_context=context_gatherer.prepare_context_for_action,
        context_args=context_args,
    )

    stages = parse_action_process_stages(data=raw)

    return stages  # noqa: RET504


@convert_bundle_errors_to_adcm_ex
def render_config(
    template: Template,
    environment: Environment,
    context_args: ActionArgs,
    context_gatherer: ContextGatherer,
) -> list[PrototypeConfig]:
    raw = _render_template(
        template=template,
        environment=environment,
        build_context=context_gatherer.prepare_context_for_action,
        context_args=context_args,
    )

    parsing_context = ConfigConversionContext(
        bundle_root=environment.bundle_root,
        path=str(template.file.path.parent),
        object={"config_group_customization": False},
    )
    config_prototypes = parse_config_jinja(
        data=raw,
        context=parsing_context,
        action=context_args.action,
    )

    return config_prototypes  # noqa: RET504


@convert_bundle_errors_to_adcm_ex
def render_scripts(
    template: Template,
    environment: Environment,
    context_args: TaskArgs,
    context_gatherer: ContextGatherer,
) -> list[JobSpec]:
    raw = _render_template(
        template=template,
        environment=environment,
        build_context=context_gatherer.prepare_context_for_task,
        context_args=context_args,
    )

    schema = DynamicScriptsSchema if context_args.wizard_process_id is None else WizardScriptsSchema

    allow_to_terminate_from_action = context_args.action.allow_to_terminate
    parsing_context = ScriptsConversionContext(
        source_dir=template.file.path.parent, action_allow_to_terminate=allow_to_terminate_from_action
    )

    scripts = parse_scripts(data=raw, context=parsing_context, schema=schema)

    return scripts  # noqa: RET504


@convert_bundle_errors_to_adcm_ex
def render_hc_template(
    template: Template,
    environment: Environment,
    context_args: TaskArgs,
    context_gatherer: ContextGatherer,
) -> list[core.mapping.MappingRule]:
    raw = _render_template(
        template=template,
        environment=environment,
        build_context=context_gatherer.prepare_context_for_task,
        context_args=context_args,
    )
    rules = [core.mapping.MappingRule(**rule) for rule in raw]

    cluster_id = _retrieve_related_cluster_id(object_=context_args.target_object)
    _validate_mapping_spec(spec=rules, cluster_id=cluster_id)

    return rules


# Helper Functions

T = TypeVar("T")


def _render_template(
    template: Template,
    environment: Environment,
    build_context: Callable[[T], dict],
    context_args: T,
) -> list[dict]:
    context = build_context(context_args)
    # TODO: Decryption of the Ansible secret is a relatively fast operation.
    #  But decrypting 192 secret fields takes about 1.8 seconds. See bundle from ADCM-7481.
    #  It seems we can optimize this. I think that for template rendering,
    #  we may not encrypt the fields when preparing the context in order to decrypt them later.
    decrypted_context = decrypt_secrets(context)

    renderer = get_renderer(template=template, environment=RendererEnv(discovery_root=environment.bundle_root))
    result = renderer.render(context=decrypted_context)

    typed_result = _ensure_render_result_is_list_of_dicts(result)

    return typed_result  # noqa: RET504


def _ensure_render_result_is_list_of_dicts(value: Any) -> list[dict]:
    if not isinstance(value, list) and all(isinstance(e, dict) for e in value):
        message = "Rendering result for scripts is expected to be list of dicts"
        raise TypeError(message)

    return value


def _validate_mapping_spec(spec: list[core.mapping.MappingRule], cluster_id: ClusterID) -> None:
    db_component_keys = repo.retrieve_cluster_component_definition_keys(cluster_id=cluster_id)
    check_action_hc_acl_rules(hostcomponentmap=[asdict(rule) for rule in spec], definitions=db_component_keys)


def _retrieve_related_cluster_id(object_: Cluster | Service | Component | Host | ActionHostGroup) -> ClusterID:
    if isinstance(object_, ActionHostGroup):
        return _retrieve_related_cluster_id(object_=object_.object)

    elif isinstance(object_, Cluster):
        return object_.id

    else:
        return object_.cluster_id
