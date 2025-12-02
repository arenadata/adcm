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

from typing import Collection, TypedDict

from cm.legacy.api import add_host
from cm.legacy.services.job.run import create_related_configs
from cm.models import Prototype, Provider
from core.legacy.job.types import RelatedObjects, TaskOwner
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.db import IntegrityError
from django.db.transaction import atomic

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    BaseStrictModel,
    CallResult,
    ContextConfig,
    PluginExecutorConfig,
    ReturnValue,
    RuntimeEnvironment,
)
from ansible_plugin.errors import PluginRuntimeError


class AddHostArguments(BaseStrictModel):
    fqdn: str
    description: str = ""


class AddHostReturnValue(TypedDict):
    host_id: int


class ADCMAddHostPluginExecutor(ADCMAnsiblePluginExecutor[AddHostArguments, AddHostReturnValue]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=AddHostArguments),
        context=ContextConfig(allow_only=frozenset({ADCMCoreType.PROVIDER})),
    )

    def __call__(
        self, targets: Collection[CoreObjectDescriptor], arguments: AddHostArguments, runtime: RuntimeEnvironment
    ) -> CallResult[ReturnValue]:
        _ = targets

        with atomic():
            try:
                provider = Provider.objects.select_related("prototype__bundle").get(id=runtime.context_owner.id)
                host_prototype = Prototype.objects.get(type="host", bundle=provider.prototype.bundle)
                host = add_host(
                    provider=provider,
                    prototype=host_prototype,
                    fqdn=arguments.fqdn,
                    description=arguments.description,
                )
                task_owner = TaskOwner(
                    id=runtime.context_owner.id,
                    type=runtime.context_owner.type,
                    name=provider.name,
                    prototype_id=provider.prototype_id,
                    related_objects=RelatedObjects(),
                )
                # In fact, we are not creating new related_configs, but updating them.
                # Since hosts are created while jobs are running.
                create_related_configs(job_id=runtime.vars.job.id, owner=task_owner)
            except Provider.DoesNotExist:
                return CallResult(
                    value=None,
                    changed=False,
                    error=PluginRuntimeError(message=f"Failed to find Provider with id {runtime.context_owner.id}"),
                )
            except Prototype.DoesNotExist:
                return CallResult(
                    value=None,
                    changed=False,
                    error=PluginRuntimeError(
                        message="Failed to locate host's prototype based on Provider "
                        f"with id {runtime.context_owner.id}"
                    ),
                )
            except IntegrityError as err:
                return CallResult(
                    value=None,
                    changed=False,
                    error=PluginRuntimeError(message=f"Failed to create host due to IntegrityError: {err}"),
                )

        return CallResult(value=AddHostReturnValue(host_id=int(host.pk)), changed=True, error=None)
