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

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from functools import reduce
from itertools import chain
from operator import or_
from typing import Collection

from core.types import CoreObjectDescriptor
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from cm.converters import core_type_to_model, model_name_to_core_type
from cm.hierarchy import Tree
from cm.issue import add_concern_to_object, remove_concern_from_object
from cm.models import ADCMEntity, ConcernCause, ConcernItem, ConcernType
from cm.services.concern.distribution import distribute_concern_on_related_objects
from cm.services.concern.messages import (
    ADCM_ENTITY_AS_PLACEHOLDERS,
    ConcernMessage,
    ConcernMessageTemplate,
    PlaceholderObjectsDTO,
    build_concern_reason,
)


@dataclass(slots=True, frozen=True)
class ConcernFlag:
    name: str
    message: str
    cause: ConcernCause | None = None


class BuiltInFlag(Enum):
    ADCM_OUTDATED_CONFIG = ConcernFlag(
        name="adcm_outdated_config", message="outdated config", cause=ConcernCause.CONFIG
    )


def raise_flag(flag: ConcernFlag, on_objects: Collection[CoreObjectDescriptor]) -> bool:
    """Returns whether any objects were affected or not"""
    message_template = ConcernMessageTemplate(
        message=f"{ConcernMessage.FLAG.value.message}{flag.message}".rstrip(": "),
        placeholders=ADCM_ENTITY_AS_PLACEHOLDERS,
    )

    content_type_id_map = _get_owner_ids_grouped_by_content_type(objects=on_objects)

    existing_concerns = ConcernItem.objects.filter(
        Q(name=flag.name) & _get_filter_for_flags_of_objects(content_type_id_map=content_type_id_map)
    )

    processed_objects: dict[ContentType, set[int]] = {content_type: set() for content_type in content_type_id_map}
    concerns_to_update = []
    for concern in existing_concerns:
        if concern.reason["message"] != message_template.message:
            concern.reason["message"] = message_template.message
            concerns_to_update.append(concern)

        processed_objects[concern.owner_type].add(concern.owner_id)

    if concerns_to_update:
        ConcernItem.objects.bulk_update(objs=concerns_to_update, fields=["reason"])

    objects_without_flags: tuple[ADCMEntity, ...] = tuple(
        chain.from_iterable(
            content_type.model_class().objects.filter(id__in=requested_ids - processed_objects[content_type])
            for content_type, requested_ids in content_type_id_map.items()
        )
    )

    if not objects_without_flags:
        return bool(concerns_to_update)

    ConcernItem.objects.bulk_create(
        objs=(
            ConcernItem(
                owner=object_,
                type=ConcernType.FLAG,
                cause=flag.cause,
                name=flag.name,
                blocking=False,
                reason=build_concern_reason(
                    template=message_template, placeholder_objects=PlaceholderObjectsDTO(source=object_)
                ),
            )
            for object_ in objects_without_flags
        )
    )

    return bool(concerns_to_update or objects_without_flags)


def lower_flag(name: str, on_objects: Collection[CoreObjectDescriptor]) -> bool:
    deleted_count, _ = ConcernItem.objects.filter(
        Q(name=name)
        & _get_filter_for_flags_of_objects(
            content_type_id_map=_get_owner_ids_grouped_by_content_type(objects=on_objects)
        )
    ).delete()
    return bool(deleted_count)


def lower_all_flags(on_objects: Collection[CoreObjectDescriptor]) -> bool:
    deleted_count, _ = ConcernItem.objects.filter(
        _get_filter_for_flags_of_objects(content_type_id_map=_get_owner_ids_grouped_by_content_type(objects=on_objects))
    ).delete()
    return bool(deleted_count)


def update_hierarchy_for_flag(flag: ConcernFlag, on_objects: Collection[CoreObjectDescriptor]) -> None:
    for concern in ConcernItem.objects.select_related("owner_type").filter(
        Q(name=flag.name, cause=flag.cause, type=ConcernType.FLAG)
        & _get_filter_for_flags_of_objects(
            content_type_id_map=_get_owner_ids_grouped_by_content_type(objects=on_objects)
        )
    ):
        owner = CoreObjectDescriptor(id=concern.owner_id, type=model_name_to_core_type(concern.owner_type.model))
        distribute_concern_on_related_objects(owner=owner, concern_id=concern.id)
        # update_hierarchy(concern)


def update_hierarchy(concern: ConcernItem) -> None:
    tree = Tree(obj=concern.owner)

    related = set(concern.related_objects)
    affected = {node.value for node in tree.get_directly_affected(node=tree.built_from)}

    if related == affected:
        return

    for object_moved_out_hierarchy in related.difference(affected):
        remove_concern_from_object(object_=object_moved_out_hierarchy, concern=concern)

    for new_object in affected.difference(related):
        add_concern_to_object(object_=new_object, concern=concern)


def _get_filter_for_flags_of_objects(content_type_id_map: dict[ContentType, set[int]]) -> Q:
    return Q(type=ConcernType.FLAG) & reduce(
        or_,
        (
            Q(owner_type=content_type, owner_id__in=object_ids)
            for content_type, object_ids in content_type_id_map.items()
        ),
    )


def _get_owner_ids_grouped_by_content_type(objects: Collection[CoreObjectDescriptor]) -> dict[ContentType, set[int]]:
    core_to_model_map = {object_.type: core_type_to_model(object_.type) for object_ in objects}
    model_content_type_map = {
        content_type.model: content_type
        for content_type in ContentType.objects.filter(
            app_label="cm", model__in={model.__name__.lower() for model in core_to_model_map.values()}
        )
    }

    result = defaultdict(set)
    for object_ in objects:
        model = core_to_model_map[object_.type]
        result[model_content_type_map[model.__name__.lower()]].add(object_.id)

    return result
