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

from core.types import ConcernID, HostID
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
    get_raw_status as legacy_get_raw_status,
)
from cm.legacy.status_api import (
    notify_about_new_concern as legacy_notify_about_new_concern,
)
from cm.legacy.status_api import (
    notify_about_redistributed_concerns_from_maps as legacy_notify_about_redistributed_concerns_from_maps,
)
from cm.legacy.status_api import (
    send_object_update_event as legacy_send_object_update_event,
)


@dataclass(slots=True)
class StatusScenarios:
    def retrieve_status_map(self) -> FullStatusMap:
        return legacy_retrieve_status_map()

    def get_raw_status(self, url: str) -> int:
        return legacy_get_raw_status(url=url)

    def send_object_update_event(self, obj_id: int, obj_type: str, changes: dict) -> None:
        legacy_send_object_update_event(obj_id=obj_id, obj_type=obj_type, changes=changes)

    def notify_about_redistributed_concerns_from_maps(
        self,
        added: AffectedObjectConcernMap,
        removed: AffectedObjectConcernMap,
    ) -> None:
        legacy_notify_about_redistributed_concerns_from_maps(added=added, removed=removed)

    def notify_about_new_concern(self, concern_id: ConcernID, related_objects: ConcernRelatedObjects) -> None:
        legacy_notify_about_new_concern(concern_id=concern_id, related_objects=related_objects)

    def update_all(self) -> None:
        legacy_update_all()

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
        return legacy_reset_objects_in_mm()
