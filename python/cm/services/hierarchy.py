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

from core.types import ADCMCoreType, CoreObjectDescriptor, ObjectID

from cm.converters import core_type_to_model
from cm.models import Component, Host, Service


def retrieve_object_hierarchy(object_: CoreObjectDescriptor) -> dict[ADCMCoreType, set[ObjectID]]:
    """Returns object's cluster-service-component, provider-host or ADCM hierarchy"""

    match object_.type:
        case ADCMCoreType.CLUSTER | ADCMCoreType.SERVICE | ADCMCoreType.COMPONENT:
            if object_.type == ADCMCoreType.CLUSTER:
                cluster_id = object_.id
            else:
                cluster_id = (
                    core_type_to_model(object_.type).objects.values_list("cluster_id", flat=True).get(id=object_.id)
                )

            hierarchy = {ADCMCoreType.CLUSTER: {cluster_id}}

            if service_ids := set(Service.objects.filter(cluster_id=cluster_id).values_list("id", flat=True)):
                hierarchy.update({ADCMCoreType.SERVICE: service_ids})

            if component_ids := set(Component.objects.filter(cluster_id=cluster_id).values_list("id", flat=True)):
                hierarchy.update({ADCMCoreType.COMPONENT: component_ids})

            return hierarchy

        case ADCMCoreType.HOST:
            provider_id = Host.objects.values_list("provider_id", flat=True).get(id=object_.id)
            return {object_.type: {object_.id}, ADCMCoreType.PROVIDER: {provider_id}}

        case _:
            return {object_.type: {object_.id}}
