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

from core.types import ADCMCoreType

from cm.models import Cluster, ClusterObject, Host, HostProvider, ServiceComponent


def core_type_to_model(
    core_type: ADCMCoreType,
) -> type[Cluster | ClusterObject | ServiceComponent | HostProvider | Host]:
    match core_type:
        case ADCMCoreType.CLUSTER:
            return Cluster
        case ADCMCoreType.SERVICE:
            return ClusterObject
        case ADCMCoreType.COMPONENT:
            return ServiceComponent
        case ADCMCoreType.HOSTPROVIDER:
            return HostProvider
        case ADCMCoreType.HOST:
            return Host
        case _:
            raise ValueError(f"Can't convert {core_type} to ORM model")


def model_name_to_core_type(model_name: str) -> ADCMCoreType:
    try:
        return ADCMCoreType(model_name)
    except ValueError:
        if model_name == "clusterobject":
            return ADCMCoreType.SERVICE

        if model_name == "servicecomponent":
            return ADCMCoreType.COMPONENT

        raise
