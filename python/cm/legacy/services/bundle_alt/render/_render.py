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

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar

from core.legacy.bundle_alt.process import (
    ConfigConversionContext,
    ScriptsConversionContext,
    parse_action_process_stages,
    parse_scripts,
)
from core.legacy.bundle_alt.schema import ActionProcessStage, DynamicScriptsSchema, WizardScriptsSchema
from core.legacy.bundle_alt.validation import check_action_hc_acl_rules
from core.legacy.job.types import JobSpec, MappingRule
from core.templates import RendererEnv, Template, get_renderer

from cm.legacy.services.action_process import repo
from cm.legacy.services.bundle_alt.errors import convert_bundle_errors_to_adcm_ex
from cm.legacy.services.bundle_alt.load import parse_config_jinja
from cm.legacy.services.bundle_alt.render._context import (
    ActionArgs,
    TaskArgs,
    prepare_context_for_action,
    prepare_context_for_task,
)
from cm.legacy.utils import decrypt_secrets
from cm.models import Cluster, Component, PrototypeConfig, Service


@dataclass(slots=True)
class Environment:
    bundle_root: Path


# Render by Target


@convert_bundle_errors_to_adcm_ex
def render_process(
    template: Template,
    environment: Environment,
    context_args: ActionArgs,
) -> list[ActionProcessStage]:
    raw = _render_template(
        template=template, environment=environment, build_context=prepare_context_for_action, context_args=context_args
    )

    stages = parse_action_process_stages(data=raw)

    return stages  # noqa: RET504


@convert_bundle_errors_to_adcm_ex
def render_config(
    template: Template,
    environment: Environment,
    context_args: ActionArgs,
) -> list[PrototypeConfig]:
    raw = _render_template(
        template=template, environment=environment, build_context=prepare_context_for_action, context_args=context_args
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
) -> list[JobSpec]:
    raw = _render_template(
        template=template,
        environment=environment,
        build_context=prepare_context_for_task,
        context_args=context_args,
    )

    schema = DynamicScriptsSchema if context_args.action_process is None else WizardScriptsSchema

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
) -> list[MappingRule]:
    raw = _render_template(
        template=template,
        environment=environment,
        build_context=prepare_context_for_task,
        context_args=context_args,
    )
    rules = [MappingRule(**rule) for rule in raw]
    _validate_mapping_spec(spec=rules, object_=context_args.target_object)

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


def _validate_mapping_spec(spec: list[MappingRule], object_: Cluster | Service | Component) -> None:
    cluster_id = object_.id if isinstance(object_, Cluster) else object_.cluster_id
    db_component_keys = repo.retrieve_cluster_component_definition_keys(cluster_id=cluster_id)
    check_action_hc_acl_rules(hostcomponentmap=[rule.model_dump() for rule in spec], definitions=db_component_keys)
