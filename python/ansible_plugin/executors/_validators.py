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

from operator import attrgetter

from core.types import ADCMCoreType, CoreObjectDescriptor

from ansible_plugin.errors import PluginTargetError

_CLUSTER_TYPES = {ADCMCoreType.CLUSTER, ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT}
_HOSTPROVIDER_TYPES = {ADCMCoreType.HOSTPROVIDER, ADCMCoreType.HOST}
_ALLOWED_CONTEXT_OWNER_MAP: dict[ADCMCoreType, set[ADCMCoreType]] = {
    ADCMCoreType.CLUSTER: _CLUSTER_TYPES,
    ADCMCoreType.SERVICE: _CLUSTER_TYPES,
    ADCMCoreType.COMPONENT: _CLUSTER_TYPES,
    ADCMCoreType.HOSTPROVIDER: _HOSTPROVIDER_TYPES,
    ADCMCoreType.HOST: _HOSTPROVIDER_TYPES,
}


def validate_target_allowed_for_context_owner(
    context_owner: CoreObjectDescriptor, target: CoreObjectDescriptor
) -> PluginTargetError | None:
    """
    Some plugins allow to target not the current object or "directly related" one,
    so we want to check if such mutation is allowed.
    This is the main implementation of this rule, there may be others like that,
    but this one is based on `adcm_config` rules.
    """

    owner_types = _ALLOWED_CONTEXT_OWNER_MAP[target.type]
    if context_owner.type not in owner_types:
        return PluginTargetError(
            message="Wrong context. "
            f"Affecting {target.type.value} isn't allowed from {context_owner.type.value}. "
            f"Allowed: {', '.join(sorted(map(attrgetter('value'), owner_types)))}."
        )

    if target.type == ADCMCoreType.HOST and target.id != context_owner.id:
        # only case it'll happen (in terms of plugin call):
        # context is "host" AND "type" is "host" AND "host_id" is specified as not the same as one in context
        return PluginTargetError(message="Wrong context. One host can't be changed from another's context.")

    return None
