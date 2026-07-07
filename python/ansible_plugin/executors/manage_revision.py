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
from enum import Enum

from core.types import CoreObjectDescriptor
from use_cases.transition.config_revision import DiffValue, FindPrimaryConfigDiff, SetPrimaryConfigRevision

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    BaseArgumentsWithTypedObjects,
    CallResult,
    PluginExecutorConfig,
    RuntimeEnvironment,
    TargetConfig,
    from_objects,
)
from ansible_plugin.errors import PluginValidationError


class Operation(str, Enum):
    GET_PRIMARY_DIFF = "get_primary_diff"
    SET_PRIMARY_REVISION = "set_primary_revision"


class ManageRevisionArguments(BaseArgumentsWithTypedObjects):
    operation: Operation


def validate_objects(arguments: ManageRevisionArguments) -> PluginValidationError | None:
    """
    Check that at least one object is passed and all passed objects belong to cluster or provider hierarchy.
    """

    cluster_types = {"cluster", "service", "component"}
    provider_types = {"provider", "host"}

    object_types = {obj.type for obj in arguments.objects}

    if not object_types:
        return PluginValidationError("At least one object must be specified")

    in_cluster_types = bool(object_types.intersection(cluster_types))
    in_provider_types = bool(object_types.intersection(provider_types))
    if (in_cluster_types and in_provider_types) or not (in_cluster_types or in_provider_types):
        return PluginValidationError(f"Target objects must belong to {cluster_types} or {provider_types} hierarchy")


class ADCMManageRevisionPluginExecutor(ADCMAnsiblePluginExecutor[ManageRevisionArguments, DiffValue | None]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=ManageRevisionArguments, validators=(validate_objects,)),
        target=TargetConfig(detectors=(from_objects,)),
    )

    def __call__(
        self, targets: Collection[CoreObjectDescriptor], arguments: ManageRevisionArguments, runtime: RuntimeEnvironment
    ) -> CallResult[DiffValue | None]:
        match arguments.operation:
            case Operation.SET_PRIMARY_REVISION:
                set_primary_config_revision = self._container.get(SetPrimaryConfigRevision)
                has_changed = set_primary_config_revision.do(targets=targets, job_id=runtime.vars.job.id)
                return CallResult(value=None, changed=has_changed, error=None)

            case Operation.GET_PRIMARY_DIFF:
                find_primary_config_diff = self._container.get(FindPrimaryConfigDiff)
                diff = find_primary_config_diff.do(targets=targets, job_id=runtime.vars.job.id)
                return CallResult(value=diff, changed=False, error=None)
