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

from dataclasses import dataclass
from typing import cast

from core.action import operations
from core.result import Fail, Success
from core.types import (
    ActionID,
    ActionTargetDescriptor,
    ADCMCoreType,
    ClusterDesc,
    ClusterObjectDesc,
    CoreObjectDescriptor,
    Descriptor,
    ExtraActionTargetType,
    ProviderDesc,
    ProviderObjectDesc,
)
import core


@dataclass(slots=True)
class RetrieveStartImpossibleReason:
    cluster_service: core.cluster.ClusterService
    provider_service: core.provider.ProviderService
    config_service: core.config.ConfigService

    def for_action_target(
        self, target: ActionTargetDescriptor, allowed_in_mm: dict[ActionID, bool]
    ) -> dict[ActionID, operations.StartImpossibleReason | None]:
        if target.type == ExtraActionTargetType.ACTION_HOST_GROUP:
            target_desc = self.cluster_service.repo.get_ahg_owner(ahg_id=target.id)
        else:  # convert to Descriptor
            target_desc = Descriptor(id=target.id, type=target.type)

        match target_desc:
            case Descriptor(type=ADCMCoreType.PROVIDER):
                return {id_: None for id_ in allowed_in_mm}

            case Descriptor(type=ADCMCoreType.ADCM):
                adcm_config = self.config_service.retrieve_current_configuration(
                    owner=CoreObjectDescriptor(id=target_desc.id, type=ADCMCoreType.ADCM)
                )
                result = operations.detect_start_impossible_reason_for_adcm(
                    ldap_integration_attr=adcm_config.attributes["/ldap_integration"]
                )

                match result:
                    case Fail(value=(reason)):
                        return {id_: reason.value for id_ in allowed_in_mm}

            case Descriptor(type=ADCMCoreType.HOST):
                mm = self.provider_service.retrieve_own_maintenance_mode(target=cast(ProviderObjectDesc, target_desc))
                result = operations.detect_start_impossible_reason_for_provider_objects(maintenance_mode=mm)

            case _:  # in cluster hierarchy
                target_desc = cast(ClusterObjectDesc, target_desc)
                cluster_id = self.cluster_service.repo.get_related_cluster_id(object_=target_desc)

                topology = self.cluster_service.retrieve_topology(cluster_id=cluster_id)
                own_mm = self.cluster_service.retrieve_own_maintenance_mode(cluster_ids=(cluster_id,))
                objects_mm = self.cluster_service.calculate_maintenance_mode(topology=topology, objects_own_mm=own_mm)

                result = operations.detect_start_impossible_reason_for_cluster_objects(
                    target=target_desc, topology=topology, maintenance_mode=objects_mm
                )

        match result:
            case Success():
                return {action_id: None for action_id in allowed_in_mm}

            case Fail(value=(reason, type_)):
                match reason:
                    case operations.ActionStartImpossibleReason.LDAP_OFF:
                        msg = reason.value
                    case operations.ActionStartImpossibleReason.MAINTENANCE_MODE:
                        msg = reason.value.format(entity_type="Action", violator_type=f"{type_.value}s")

                return {id_: None if is_allowed_in_mm else msg for id_, is_allowed_in_mm in allowed_in_mm.items()}

    def for_upgrade_target(self, target: ClusterDesc | ProviderDesc) -> operations.StartImpossibleReason | None:
        match target:
            case Descriptor(type=ADCMCoreType.PROVIDER):
                objects_mm = self.provider_service.retrieve_own_maintenance_mode(target=target)
                result = operations.detect_start_impossible_reason_for_provider_objects(maintenance_mode=objects_mm)

            case Descriptor(type=ADCMCoreType.CLUSTER):
                topology = self.cluster_service.retrieve_topology(cluster_id=target.id)
                own_mm = self.cluster_service.retrieve_own_maintenance_mode(cluster_ids=(target.id,))
                objects_mm = self.cluster_service.calculate_maintenance_mode(topology=topology, objects_own_mm=own_mm)
                result = operations.detect_start_impossible_reason_for_cluster_objects(
                    target=target, topology=topology, maintenance_mode=objects_mm
                )

            case _:
                raise TypeError(f"Unexpected target: {target}")

        match result:
            case Success():
                return None
            case Fail(value=(reason, type_)):
                return reason.value.format(entity_type="Upgrade", violator_type=f"{type_.value}s")
