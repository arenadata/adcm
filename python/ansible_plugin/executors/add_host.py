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

from cm.api import add_host
from cm.models import HostProvider, Prototype
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.db import IntegrityError
from django.db.transaction import atomic
from pydantic import BaseModel

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    AnsibleJobContext,
    ArgumentsConfig,
    CallResult,
    PluginExecutorConfig,
    ReturnValue,
    TargetConfig,
    from_context,
)
from ansible_plugin.errors import PluginRuntimeError, PluginTargetError


class AddHostArguments(BaseModel):
    fqdn: str
    description: str = ""


class AddHostReturnValue(TypedDict):
    host_id: int


class ADCMAddHostPluginExecutor(ADCMAnsiblePluginExecutor[AddHostArguments, AddHostReturnValue]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=AddHostArguments), target=TargetConfig(detectors=(from_context,))
    )

    def __call__(
        self,
        targets: Collection[CoreObjectDescriptor],
        arguments: AddHostArguments,
        context_owner: CoreObjectDescriptor,
        context: AnsibleJobContext,
    ) -> CallResult[ReturnValue]:
        _ = targets, context

        target = context_owner

        if target.type != ADCMCoreType.HOSTPROVIDER:
            message = f"Plugin should be called only in context of hostprovider, not {target.type.value}"
            raise PluginTargetError(message)

        with atomic():
            try:
                hostprovider = HostProvider.objects.select_related("prototype__bundle").get(id=target.id)
                host_prototype = Prototype.objects.get(type="host", bundle=hostprovider.prototype.bundle)
                host = add_host(
                    provider=hostprovider,
                    prototype=host_prototype,
                    fqdn=arguments.fqdn,
                    description=arguments.description,
                )
            except HostProvider.DoesNotExist as err:
                return CallResult(
                    value=None,
                    changed=False,
                    error=PluginRuntimeError(
                        message=f"Failed to find HostProvider with id {target.id}", original_error=err
                    ),
                )
            except Prototype.DoesNotExist as err:
                return CallResult(
                    value=None,
                    changed=False,
                    error=PluginRuntimeError(
                        message=f"Failed to locate host's prototype based on HostProvider with id {target.id}",
                        original_error=err,
                    ),
                )
            except IntegrityError as err:
                return CallResult(
                    value=None,
                    changed=False,
                    error=PluginRuntimeError(
                        message=f"Failed to create host due to IntegrityError: {err}", original_error=err
                    ),
                )

        return CallResult(value=AddHostReturnValue(host_id=int(host.pk)), changed=True, error=None)
