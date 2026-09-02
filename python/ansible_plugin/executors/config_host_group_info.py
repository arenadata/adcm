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

from collections.abc import Collection

from cm.models import ConfigHostGroup
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.contrib.contenttypes.models import ContentType

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    BaseTypedArguments,
    CallResult,
    PluginExecutorConfig,
    RuntimeEnvironment,
    TargetConfig,
    from_arguments_root,
    retrieve_orm_object,
)
from ansible_plugin.errors import PluginRuntimeError


class ConfigHostGroupInfoArguments(BaseTypedArguments):
    name: str | None = None


class ADCMConfigHostGroupInfoPluginExecutor(ADCMAnsiblePluginExecutor[ConfigHostGroupInfoArguments, dict]):
    """
    Report the configuration host groups of an object without changing anything.

    Returns every group of the target with its hosts. When `name` is given, additionally
    reports whether that group exists and which fqdns it holds, so the caller doesn't have
    to dig them out of the list.
    """

    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=ConfigHostGroupInfoArguments),
        target=TargetConfig(detectors=(from_arguments_root,)),
    )

    def __call__(
        self,
        targets: Collection[CoreObjectDescriptor],
        arguments: ConfigHostGroupInfoArguments,
        runtime: RuntimeEnvironment,
    ) -> CallResult[dict]:
        _ = runtime

        target, *_ = targets
        if target.type == ADCMCoreType.HOST:
            return CallResult(
                value={},
                changed=False,
                error=PluginRuntimeError(message="Configuration host groups can't belong to a host"),
            )

        owner = retrieve_orm_object(object_=target)

        groups = [
            {
                "id": group.pk,
                "name": group.name,
                "description": group.description,
                "hosts": sorted(group.hosts.values_list("fqdn", flat=True)),
            }
            for group in ConfigHostGroup.objects.filter(
                object_id=owner.pk, object_type=ContentType.objects.get_for_model(model=owner)
            ).order_by("name")
        ]

        value = {"groups": groups, "names": [group["name"] for group in groups]}

        if arguments.name is not None:
            named = next((group for group in groups if group["name"] == arguments.name), None)
            value |= {"exists": named is not None, "hosts": named["hosts"] if named else []}

        return CallResult(value=value, changed=False, error=None)
