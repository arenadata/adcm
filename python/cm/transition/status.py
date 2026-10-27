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

from collections.abc import Iterable
from dataclasses import dataclass

from core.cluster import ClusterService
from core.concern.repo import ConcernRepoI
from core.scenarios.status import StatusScenariosI
from core.tools import convert_keys_to_camel_case
from core.types import ADCMCoreType, ConcernID, CoreObjectDescriptor, Descriptor, HostID, ObjectID
from requests import Response

from cm.legacy.services.concern.distribution import AffectedObjectConcernMap, ConcernRelatedObjects
from cm.legacy.services.status.client import FullStatusMap
from cm.legacy.services.status.client import retrieve_status_map as legacy_retrieve_status_map
from cm.legacy.services.status.notify import (
    register_all_duplicates as legacy_register_all_duplicates,
)
from cm.legacy.services.status.notify import (
    register_host_duplicates as legacy_register_host_duplicates,
)
from cm.legacy.services.status.notify import (
    reset_hc_map as legacy_reset_hc_map,
)
from cm.legacy.services.status.notify import (
    reset_objects_in_mm as legacy_reset_objects_in_mm,
)
from cm.legacy.services.status.notify import (
    update_all as legacy_update_all,
)
from cm.legacy.status_api import (
    EventTypes,
    api_request,
    fix_object_type,
    post_event,
)
from cm.legacy.status_api import (
    send_config_creation_event as legacy_send_config_creation_event,
)
from cm.legacy.status_api import (
    send_object_update_event as legacy_send_object_update_event,
)
from cm.legacy.status_api import (
    send_prototype_and_state_update_event as legacy_send_prototype_and_state_update_event,
)
from cm.legacy.status_api import (
    send_task_status_update_event as legacy_send_task_status_update_event,
)
from cm.models import ADCMEntity

EMPTY_REQUEST_STATUS_CODE = 32
VALUE_ERROR_STATUS_CODE = 8
EMPTY_STATUS_STATUS_CODE = 4


@dataclass(slots=True)
class StatusScenarios(StatusScenariosI):
    cluster_service: ClusterService
    concern_repo: ConcernRepoI

    def retrieve_status_map(self) -> FullStatusMap:
        return legacy_retrieve_status_map()

    def get_raw_status(self, url: str) -> int:
        response = api_request(method="get", url=url)
        if response is None:
            return EMPTY_REQUEST_STATUS_CODE

        try:
            json_data = response.json()
        except ValueError:
            return VALUE_ERROR_STATUS_CODE

        if "status" in json_data:
            return json_data["status"]
        return EMPTY_STATUS_STATUS_CODE

    def send_object_update_event(self, obj_id: int, obj_type: str, changes: dict) -> None:
        legacy_send_object_update_event(obj_id=obj_id, obj_type=obj_type, changes=changes)

    def send_config_creation_event(self, owner: CoreObjectDescriptor | Descriptor, created_by: str) -> None:
        legacy_send_config_creation_event(
            object_id=owner.id,
            object_type=owner.type.value,
            changes={"createdBy": created_by},
        )

    def send_task_status_update_event(self, task_id: int, status: str) -> None:
        legacy_send_task_status_update_event(task_id=task_id, status=status)

    def send_prototype_and_state_update_event(self, object_: ADCMEntity) -> None:
        legacy_send_prototype_and_state_update_event(object_=object_)

    def send_delete_service_event(self, service_id: int) -> Response | None:
        return post_event(event=EventTypes.DELETE_SERVICE, object_id=service_id)

    def notify_about_redistributed_concerns_from_maps(
        self,
        added: AffectedObjectConcernMap,
        removed: AffectedObjectConcernMap,
    ) -> None:
        self._notify_about_redistributed_concerns(
            added=_flatten_concerns_map(added),
            removed=_flatten_concerns_map(removed),
        )

    def notify_about_new_concern(self, concern_id: ConcernID, related_objects: ConcernRelatedObjects) -> None:
        self._notify_about_redistributed_concerns(
            added=(
                (core_type, object_id, concern_id)
                for core_type, object_ids in related_objects.items()
                for object_id in object_ids
            ),
            removed=(),
        )

    def _notify_about_redistributed_concerns(
        self,
        added: Iterable[tuple[ADCMCoreType, ObjectID, ConcernID]],
        removed: Iterable[tuple[ADCMCoreType, ObjectID, ConcernID]],
    ) -> None:
        added_concerns = tuple(added)
        serialized_concerns = {
            concern.id: convert_keys_to_camel_case(
                value={
                    "id": concern.id,
                    "type": concern.type.value,
                    "reason": concern.reason,
                    "is_blocking": concern.blocking,
                    "cause": concern.cause.value if concern.cause else None,
                    "owner": {
                        "id": concern.owner.id,
                        "type": concern.owner.type.value,
                    },
                }
            )
            for concern in self.concern_repo.get_concerns_info(
                concern_ids={concern_id for _, _, concern_id in added_concerns}
            )
        }

        for core_type, object_id, concern_id in removed:
            post_event(
                event=f"delete_{fix_object_type(type_=core_type.value)}_concern",
                object_id=object_id,
                changes={"id": concern_id},
            )

        for core_type, object_id, concern_id in added_concerns:
            concern = serialized_concerns.get(concern_id)
            if concern:
                post_event(
                    event=EventTypes.CREATE_CONCERN.format(fix_object_type(type_=core_type.value)),
                    object_id=object_id,
                    changes=concern,
                )

    def update_all(self) -> None:
        legacy_update_all(cluster_service=self.cluster_service)

    def reset_hc_map(self) -> None:
        legacy_reset_hc_map()

    def update_mm_objects(self) -> Response | None:
        return self._sync_objects_in_mm()

    def reset_objects_in_mm(self) -> Response | None:
        return self._sync_objects_in_mm()

    def register_all_duplicates(self) -> None:
        legacy_register_all_duplicates()

    def register_host_duplicates(self, original: HostID, duplicates: Iterable[HostID]) -> None:
        legacy_register_host_duplicates(original=original, duplicates=duplicates)

    def _sync_objects_in_mm(self) -> Response | None:
        return legacy_reset_objects_in_mm(cluster_service=self.cluster_service)


def _flatten_concerns_map(concerns_map: AffectedObjectConcernMap) -> Iterable[tuple[ADCMCoreType, ObjectID, ConcernID]]:
    return (
        (core_type, object_id, concern_id)
        for core_type, objects in concerns_map.items()
        for object_id, concerns in objects.items()
        for concern_id in concerns
    )
