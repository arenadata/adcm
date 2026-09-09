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

from collections.abc import Callable
from typing import Literal, TypedDict, TypeVar

from cm.models import (
    ADCMEntity,
    ADCMModel,
    Cluster,
    Component,
    ConfigLog,
    Host,
    HostComponent,
    Service,
)
from cm.transition.status import StatusScenarios
from core.status import (
    EntityStatus,
    FullStatusMap,
    RawStatus,
    convert_to_component_status,
    convert_to_entity_status,
    convert_to_host_component_status,
    convert_to_service_status,
)
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer

T = TypeVar("T")


_MODEL_RETRIEVAL_FUNC_MAP: dict[type[T], Callable[[FullStatusMap, T], RawStatus | None]] = {
    Cluster: lambda status_map, cluster: status_map.get_for_cluster(cluster_id=cluster.pk),
    Service: lambda status_map, service: status_map.get_for_service(
        cluster_id=service.cluster_id, service_id=service.pk
    ),
    Component: lambda status_map, component: status_map.get_for_component(
        cluster_id=component.cluster_id, service_id=component.service_id, component_id=component.pk
    ),
    Host: lambda status_map, host: status_map.get_for_host(host_id=host.pk),
    HostComponent: lambda status_map, hc: status_map.get_for_host_component(
        cluster_id=hc.cluster_id, service_id=hc.service_id, component_id=hc.component_id, host_id=hc.host_id
    ),
}


class WithStatusSerializer(ModelSerializer):
    status = SerializerMethodField()

    def get_status(self, instance: ADCMModel) -> EntityStatus:
        status = self.context.get("status")
        if status is None:
            status_map: FullStatusMap | None = self.context.get("status_map")
            if status_map is None:
                scenarios: StatusScenarios | None = self.context.get("status_scenarios")
                if scenarios is not None:
                    status_map = scenarios.retrieve_status_map()
                    self.context["status_map"] = status_map

            if status_map is None:
                message = (
                    f"Can't detect status for {instance}, "
                    "all `status`, `status_map` and `status_scenarios` are absent in context"
                )
                raise KeyError(message)

            try:
                status = _MODEL_RETRIEVAL_FUNC_MAP[instance.__class__](status_map, instance)
            except KeyError as err:
                message = f"Don't know how to retrieve status for {instance.__class__} from status map"
                raise KeyError(message) from err

        if isinstance(instance, Service):
            return convert_to_service_status(raw_status=status, monitoring=instance.monitoring)

        if isinstance(instance, Component):
            return convert_to_component_status(raw_status=status, monitoring=instance.monitoring)

        if isinstance(instance, HostComponent):
            return convert_to_host_component_status(
                raw_status=status, component_monitoring=instance.component.monitoring
            )

        return convert_to_entity_status(raw_status=status)


class LicenseDict(TypedDict):
    status: Literal["absent", "accepted", "unaccepted"]
    text: str | None


class DependsComponentPrototypeDict(TypedDict):
    id: int
    name: str
    display_name: str
    version: str


class DependsServicePrototypeDict(TypedDict):
    id: int
    name: str
    display_name: str
    license: LicenseDict
    component_prototypes: DependsComponentPrototypeDict


class DependOnDict(TypedDict):
    service_prototype: DependsServicePrototypeDict


def get_main_info(obj: ADCMEntity | None) -> str | None:
    if obj is None or obj.config is None:
        return None

    config_log = ConfigLog.objects.filter(id=obj.config.current).first()
    if not config_log:
        return None

    return config_log.config.get("__main_info")
