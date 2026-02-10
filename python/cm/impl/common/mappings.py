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

from typing import Final

from core.types import ADCMCoreType

from cm.models import Cluster, Component, Host, Provider, Service

MAIN_CORE_TYPE_TO_MODEL: Final[dict[ADCMCoreType, type[Cluster | Service | Component | Provider | Host]]] = {
    ADCMCoreType.CLUSTER: Cluster,
    ADCMCoreType.SERVICE: Service,
    ADCMCoreType.COMPONENT: Component,
    ADCMCoreType.PROVIDER: Provider,
    ADCMCoreType.HOST: Host,
}
