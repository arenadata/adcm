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
from typing import Any, Generic, Protocol, TypeVar

from core import action, bundle, config, templates
from core.dynamic_bundle.types import ContextGathererI


class SecretsDecryptor(Protocol):
    def __call__(self, /, data: dict) -> dict:
        ...


CtxAT = TypeVar("CtxAT")
CtxTT = TypeVar("CtxTT")


@dataclass(slots=True)
class BundleRenderer(Generic[CtxAT, CtxTT]):
    context: ContextGathererI[CtxAT, CtxTT]

    secrets: config.secrets.AnsibleSecrets

    bundle_service: bundle.BundleService

    def render_config(
        self, template: templates.Template, args: CtxAT, bundle_context: bundle.BundleContext
    ) -> tuple[config.spec.FullSpec, config.Defaults]:
        render_context = self.context.prepare_context_for_action(args)

        data = self._render_template(
            template=template, encrypted_context=render_context, bundle_root=bundle_context.root
        )

        return self.bundle_service.parse_to_spec_with_defaults(
            data=data,
            bundle_context=bundle_context,
            template_path=template.file.path.parent,
        )

    def render_scripts_for_action(
        self,
        template: templates.Template,
        args: CtxTT,
        bundle_context: bundle.BundleContext,
        action_allow_to_terminate: bool,
    ) -> list[action.JobSpec]:
        render_context = self.context.prepare_context_for_task(args)

        data = self._render_template(
            template=template, encrypted_context=render_context, bundle_root=bundle_context.root
        )

        return self.bundle_service.parse_to_action_scripts(
            data=data,
            bundle_context=bundle_context,
            template_path=template.file.path.parent,
            action_allow_to_terminate=action_allow_to_terminate,
        )

    def render_scripts_for_wizard(
        self,
        template: templates.Template,
        args: CtxTT,
        bundle_context: bundle.BundleContext,
        action_allow_to_terminate: bool,
    ) -> list[action.JobSpec]:
        render_context = self.context.prepare_context_for_task(args)

        data = self._render_template(
            template=template, encrypted_context=render_context, bundle_root=bundle_context.root
        )

        return self.bundle_service.parse_to_wizard_scripts(
            data=data,
            bundle_context=bundle_context,
            template_path=template.file.path.parent,
            action_allow_to_terminate=action_allow_to_terminate,
        )

    def _render_template(
        self,
        template: templates.Template,
        encrypted_context: dict,
        bundle_root: Path,
    ) -> list[dict]:
        # TODO: Decryption of the Ansible secret is a relatively fast operation.
        #  But decrypting 192 secret fields takes about 1.8 seconds. See bundle from ADCM-7481.
        #  It seems we can optimize this. I think that for template rendering,
        #  we may not encrypt the fields when preparing the context in order to decrypt them later.
        decrypted_context = _decrypt_secrets(encrypted_context, decrypt=self.secrets.decrypt)

        template_environment = templates.RendererEnv(discovery_root=bundle_root)
        renderer = templates.get_renderer(template=template, environment=template_environment)
        rendered_data = renderer.render(context=decrypted_context)

        return _ensure_render_result_is_list_of_dicts(rendered_data)


def _ensure_render_result_is_list_of_dicts(value: Any) -> list[dict]:
    if not isinstance(value, list) and all(isinstance(e, dict) for e in value):
        message = "Rendering result is expected to be list of dicts"
        raise TypeError(message)

    return value


def _decrypt_secrets(source: dict, decrypt: config.DecryptFunc) -> dict:
    """
    Decrypt secrets in source that are in "ansible" format
    """

    result = {}

    for key, value in source.items():
        if isinstance(value, dict):
            if "__ansible_vault" in value:
                result[key] = decrypt(value["__ansible_vault"])
            else:
                result[key] = _decrypt_secrets(value, decrypt=decrypt)
        elif isinstance(value, list):
            result[key] = [
                entry if not isinstance(entry, dict) else _decrypt_secrets(entry, decrypt=decrypt) for entry in value
            ]
        else:
            result[key] = value

    return result
