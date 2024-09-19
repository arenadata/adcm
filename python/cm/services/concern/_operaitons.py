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

from itertools import chain
from typing import Iterable

from core.types import ADCMCoreType, CoreObjectDescriptor, ObjectID
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from cm.converters import core_type_to_model
from cm.models import ClusterObject, ConcernCause, ConcernItem, ConcernType, ObjectType, Prototype
from cm.services.concern.messages import ConcernMessage, PlaceholderObjectsDTO, PlaceholderTypeDTO, build_concern_reason

_issue_template_map = {
    ConcernCause.CONFIG: ConcernMessage.CONFIG_ISSUE,
    ConcernCause.IMPORT: ConcernMessage.REQUIRED_IMPORT_ISSUE,
    ConcernCause.SERVICE: ConcernMessage.REQUIRED_SERVICE_ISSUE,
    ConcernCause.HOSTCOMPONENT: ConcernMessage.HOST_COMPONENT_ISSUE,
    ConcernCause.REQUIREMENT: ConcernMessage.UNSATISFIED_REQUIREMENT_ISSUE,
}


def delete_concerns_of_removed_objects(objects: dict[ADCMCoreType, Iterable[ObjectID]]) -> None:
    query = Q()

    for type_, ids in objects.items():
        query |= Q(owner_type=core_type_to_model(type_).class_content_type, owner_id__in=ids)

    ConcernItem.objects.filter(query).delete()


def delete_issue(owner: CoreObjectDescriptor, cause: ConcernCause) -> None:
    owner_type = ContentType.objects.get_for_model(core_type_to_model(core_type=owner.type))
    ConcernItem.objects.filter(owner_id=owner.id, owner_type=owner_type, cause=cause, type=ConcernType.ISSUE).delete()


def retrieve_issue(owner: CoreObjectDescriptor, cause: ConcernCause) -> ConcernItem | None:
    owner_type = ContentType.objects.get_for_model(core_type_to_model(core_type=owner.type))
    return ConcernItem.objects.filter(
        owner_id=owner.id, owner_type=owner_type, cause=cause, type=ConcernType.ISSUE
    ).first()


def create_issue(owner: CoreObjectDescriptor, cause: ConcernCause) -> ConcernItem:
    concern_message = _issue_template_map[cause]
    target, placeholder_types_dto = _get_target_and_placeholder_types(concern_message=concern_message, owner=owner)
    reason = build_concern_reason(
        template=concern_message.template,
        placeholder_objects=PlaceholderObjectsDTO(
            source=core_type_to_model(owner.type).objects.get(pk=owner.id), target=target
        ),
        placeholder_types=placeholder_types_dto,
    )
    name = f"{cause or ''}_{ConcernType.ISSUE}".strip("_")
    owner_type = ContentType.objects.get_for_model(core_type_to_model(core_type=owner.type))

    return ConcernItem.objects.create(
        type=ConcernType.ISSUE, name=name, reason=reason, owner_id=owner.id, owner_type=owner_type, cause=cause
    )


def _get_target_and_placeholder_types(
    concern_message: ConcernMessage, owner: CoreObjectDescriptor
) -> tuple[Prototype | None, PlaceholderTypeDTO]:
    owner_prototype = Prototype.objects.values("id", "type", "bundle_id", "requires").get(
        pk=core_type_to_model(owner.type).objects.values_list("prototype_id", flat=True).get(pk=owner.id)
    )
    target = None

    match concern_message:
        case ConcernMessage.CONFIG_ISSUE:
            placeholder_type_dto = PlaceholderTypeDTO(source=f"{owner_prototype['type']}_config")

        case ConcernMessage.REQUIRED_IMPORT_ISSUE:
            placeholder_type_dto = PlaceholderTypeDTO(source="cluster_import")

        case ConcernMessage.REQUIRED_SERVICE_ISSUE:
            # owner type = cluster

            placeholder_type_dto = PlaceholderTypeDTO(source="cluster_services", target="prototype")
            target = (
                Prototype.objects.filter(
                    bundle_id=owner_prototype["bundle_id"],
                    type=ObjectType.SERVICE,
                    required=True,
                )
                .exclude(
                    id__in=ClusterObject.objects.values_list("prototype_id", flat=True).filter(cluster_id=owner.id)
                )
                .first()
            )

        case ConcernMessage.HOST_COMPONENT_ISSUE:
            placeholder_type_dto = PlaceholderTypeDTO(source="cluster_mapping")

        case ConcernMessage.UNSATISFIED_REQUIREMENT_ISSUE:
            # owner type = service

            cluster_id = ClusterObject.objects.values_list("cluster_id", flat=True).get(pk=owner.id)
            placeholder_type_dto = PlaceholderTypeDTO(source="cluster_services", target="prototype")

            required_services_names = {require["service"] for require in owner_prototype["requires"]} | set(
                chain.from_iterable(
                    (require["service"] for require in requires if "service" in require and "component" not in require)
                    for requires in Prototype.objects.filter(parent_id=owner_prototype["id"]).values_list(
                        "requires", flat=True
                    )
                )
            )
            existing_required_services = set(
                ClusterObject.objects.values_list("prototype__name", flat=True).filter(
                    cluster_id=cluster_id, prototype__name__in=required_services_names
                )
            )
            if absent_services_names := required_services_names.difference(existing_required_services):
                target = Prototype.objects.filter(
                    name__in=absent_services_names, type=ObjectType.SERVICE, bundle_id=owner_prototype["bundle_id"]
                ).first()

        case _:
            message = f"Can't detect target and placeholder for {concern_message}"
            raise RuntimeError(message)

    return target, placeholder_type_dto
