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

from typing import Callable, TypeVar

from adcm.serializers import EmptySerializer
from cm.models import (
    LICENSE_STATE,
    ADCMEntityStatus,
    ADCMModel,
    Cluster,
    Host,
    HostComponent,
    Service,
    ServiceComponent,
)
from cm.services.status.client import FullStatusMap
from cm.services.status.convert import (
    convert_to_component_status,
    convert_to_entity_status,
    convert_to_host_component_status,
    convert_to_service_status,
)
from rest_framework.fields import CharField, ChoiceField, IntegerField, SerializerMethodField
from rest_framework.serializers import ModelSerializer

T = TypeVar("T")


_MODEL_RETRIEVAL_FUNC_MAP: dict[type[T], Callable[[FullStatusMap, T], ADCMEntityStatus]] = {
    Cluster: lambda status_map, cluster: status_map.get_for_cluster(cluster_id=cluster.pk),
    Service: lambda status_map, service: status_map.get_for_service(
        cluster_id=service.cluster_id, service_id=service.pk
    ),
    ServiceComponent: lambda status_map, component: status_map.get_for_component(
        cluster_id=component.cluster_id, service_id=component.service_id, component_id=component.pk
    ),
    Host: lambda status_map, host: status_map.get_for_host(host_id=host.pk),
    HostComponent: lambda status_map, hc: status_map.get_for_host_component(
        cluster_id=hc.cluster_id, service_id=hc.service_id, component_id=hc.component_id, host_id=hc.host_id
    ),
}


class WithStatusSerializer(ModelSerializer):
    status = SerializerMethodField()

    def get_status(self, instance: ADCMModel) -> ADCMEntityStatus:
        status = self.context.get("status")
        if status is None:
            try:
                status_map = self.context["status_map"]
            except KeyError as err:
                message = f"Can't detect status for {instance}, both `status` and `status_map` are absent in context"
                raise KeyError(message) from err

            try:
                status = _MODEL_RETRIEVAL_FUNC_MAP[instance.__class__](status_map, instance)
            except KeyError as err:
                message = f"Don't know how to retrieve status for {instance.__class__} from status map"
                raise KeyError(message) from err

        if isinstance(instance, Service):
            return convert_to_service_status(raw_status=status, monitoring=instance.monitoring)

        if isinstance(instance, ServiceComponent):
            return convert_to_component_status(raw_status=status, monitoring=instance.monitoring)

        if isinstance(instance, HostComponent):
            return convert_to_host_component_status(
                raw_status=status, component_monitoring=instance.component.monitoring
            )

        return convert_to_entity_status(raw_status=status)


class LicenseSerializer(EmptySerializer):
    status = ChoiceField(choices=LICENSE_STATE)
    text = SerializerMethodField(allow_null=True)


class DependsComponentPrototypeSerializer(EmptySerializer):
    id = IntegerField()
    name = CharField()
    display_name = CharField()
    version = CharField()


class DependsServicePrototypeSerializer(EmptySerializer):
    id = IntegerField()
    name = CharField()
    display_name = CharField()
    license = LicenseSerializer()
    component_prototypes = DependsComponentPrototypeSerializer(many=True)


class DependOnSerializer(EmptySerializer):
    service_prototype = DependsServicePrototypeSerializer()
