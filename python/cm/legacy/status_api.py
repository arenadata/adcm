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
from urllib.parse import urljoin
import json

from api_v2.concern.serializers import ConcernSerializer
from core.types import (
    ADCMCoreType,
    ClusterID,
    ConcernID,
    CoreObjectDescriptor,
    ObjectID,
)
from django.conf import settings
from djangorestframework_camel_case.util import camelize
from requests import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
import requests

from cm.converters import core_type_to_model
from cm.legacy.services.concern.distribution import AffectedObjectConcernMap, ConcernRelatedObjects
from cm.logger import logger
from cm.models import (
    ADCMEntity,
    ConcernItem,
)


class EventTypes:
    CREATE_CONCERN = "create_{}_concern"
    DELETE_CONCERN = "delete_{}_concern"
    DELETE_SERVICE = "delete_service"
    UPDATE_HOSTCOMPONENTMAP = "update_hostcomponentmap"
    CREATE_CONFIG = "create_{}_config"
    UPDATE = "update_{}"


class StatusServiceUrl:
    """Base status service URL
    - in-process calls go to INTERNAL_STATUS_SERVICE_URL
    - external components (Celery workers) calls go to the external URL set at worker startup
    """

    # Deliberate process-wide override, not accidental global state: worker_init
    # sets the external URL once before the prefork pool forks, covering every
    # legacy status_api caller that bypasses StatusScenarios (job finalizers,
    # cm.signals, ansible plugins). Removing it requires routing those callers
    # through StatusScenarios/DI first — tracked as a follow-up ticket: ADCM-8276

    external: str | None = None

    @property
    def internal(self) -> str:
        # read lazily: settings must not be captured at import time
        return settings.INTERNAL_STATUS_SERVICE_URL

    def set_external(self, url: str) -> None:
        self.external = url

    def resolve(self) -> str:
        return self.external or self.internal


status_service_url = StatusServiceUrl()


def api_request(method: str, url: str, data: dict = None) -> Response | None:
    url = urljoin(status_service_url.resolve(), url)
    kwargs = {
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Token {settings.ADCM_TOKEN}",
        },
        "timeout": settings.STATUS_REQUEST_TIMEOUT,
    }

    if data is not None:
        kwargs["data"] = json.dumps(data)

    try:
        response = requests.request(method, url, **kwargs)
        if response.status_code not in {HTTP_200_OK, HTTP_201_CREATED}:
            logger.error("%s %s error %d: %s", method, url, response.status_code, response.text)
        return response  # noqa: TRY300
    except requests.exceptions.Timeout:
        logger.error("%s request to %s timed out", method, url)
        return None
    except requests.exceptions.ConnectionError:
        logger.error("%s request to %s connection failed", method, url)
        return None


def post_event(event: str, object_id: int | None, changes: dict | None = None) -> Response | None:
    if object_id is None:
        return None

    data = {
        "event": event,
        "object": {"id": object_id, **({"changes": changes} if changes else {})},
    }

    return api_request(method="post", url="event/", data=data)


def fix_object_type(type_: str) -> str:
    if type_ == "provider":
        return "hostprovider"

    return type_


def send_concern_creation_event(object_: ADCMEntity, concern: dict) -> None:
    post_event(
        event=EventTypes.CREATE_CONCERN.format(fix_object_type(type_=object_.prototype.type)),
        object_id=object_.pk,
        changes=concern,
    )


def send_concern_delete_event(object_id: int, object_type: str, concern_id: int) -> None:
    post_event(
        event=EventTypes.DELETE_CONCERN.format(fix_object_type(type_=object_type)),
        object_id=object_id,
        changes={"id": concern_id},
    )


def send_delete_service_event(service_id: int) -> Response | None:
    return post_event(
        event=EventTypes.DELETE_SERVICE,
        object_id=service_id,
    )


def send_host_component_map_update_event(cluster_id: ClusterID) -> None:
    post_event(event=EventTypes.UPDATE_HOSTCOMPONENTMAP, object_id=cluster_id)


def send_config_creation_event(object_id: int, object_type: str, changes: dict) -> None:
    post_event(
        event=EventTypes.CREATE_CONFIG.format(fix_object_type(type_=object_type)),
        object_id=object_id,
        changes=changes,
    )


def send_update_event(object_: CoreObjectDescriptor, changes: dict) -> None:
    post_event(
        event=EventTypes.UPDATE.format(fix_object_type(type_=object_.type.value)), object_id=object_.id, changes=changes
    )


def send_object_update_event(obj_id: int, obj_type: str, changes: dict) -> None:
    post_event(
        event=EventTypes.UPDATE.format(fix_object_type(obj_type)),
        object_id=obj_id,
        changes=changes,
    )


def send_task_status_update_event(task_id: int, status: str) -> None:
    post_event(event=EventTypes.UPDATE.format("task"), object_id=task_id, changes={"status": status})


def send_prototype_update_event(object_: CoreObjectDescriptor) -> None:
    # todo inplace request, no need in the whole object
    send_prototype_and_state_update_event(
        core_type_to_model(core_type=object_.type).objects.select_related("prototype").get(id=object_.id)
    )


def send_prototype_and_state_update_event(object_: ADCMEntity) -> None:
    changes = {
        "state": object_.state,
        "prototype": {
            "id": object_.prototype.pk,
            "name": object_.prototype.name,
            "displayName": object_.prototype.display_name,
            "version": object_.prototype.version,
        },
    }

    post_event(
        event=EventTypes.UPDATE.format(fix_object_type(type_=object_.prototype.type)),
        object_id=object_.pk,
        changes=changes,
    )


def get_raw_status(url: str) -> int:
    response = api_request(method="get", url=url)
    if response is None:
        return settings.EMPTY_REQUEST_STATUS_CODE

    try:
        json_data = response.json()
    except ValueError:
        return settings.VALUE_ERROR_STATUS_CODE

    if "status" in json_data:
        return json_data["status"]
    return settings.EMPTY_STATUS_STATUS_CODE


def notify_about_redistributed_concerns(
    added: Iterable[tuple[ADCMCoreType, ObjectID, ConcernID]],
    removed: Iterable[tuple[ADCMCoreType, ObjectID, ConcernID]],
) -> None:
    added_concerns = tuple(added)
    serialized_concerns = {
        concern.id: camelize(data=ConcernSerializer(instance=concern).data)
        for concern in ConcernItem.objects.filter(id__in=(id_ for _, _, id_ in added_concerns)).prefetch_related(
            "owner"
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
                event=f"create_{fix_object_type(type_=core_type.value)}_concern", object_id=object_id, changes=concern
            )


def notify_about_new_concern(concern_id: ConcernID, related_objects: ConcernRelatedObjects) -> None:
    notify_about_redistributed_concerns(
        added=(
            (core_type, object_id, concern_id)
            for core_type, object_ids in related_objects.items()
            for object_id in object_ids
        ),
        removed=(),
    )


def notify_about_redistributed_concerns_from_maps(
    added: AffectedObjectConcernMap,
    removed: AffectedObjectConcernMap,
):
    """
    Convenience function to call `notify_about_redistributed_concerns` based on input of `redistribute_issues_and_flags`
    """
    return notify_about_redistributed_concerns(
        added=_flatten_concerns_map(added),
        removed=_flatten_concerns_map(removed),
    )


def _flatten_concerns_map(concerns_map: AffectedObjectConcernMap) -> Iterable[tuple[ADCMCoreType, ObjectID, ConcernID]]:
    return (
        (core_type, object_id, concern_id)
        for core_type, objects in concerns_map.items()
        for object_id, concerns in objects.items()
        for concern_id in concerns
    )
