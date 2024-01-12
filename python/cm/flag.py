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

from cm.hierarchy import Tree
from cm.issue import add_concern_to_object, remove_concern_from_object
from cm.models import (
    ADCMEntity,
    ConcernCause,
    ConcernItem,
    ConcernType,
    KnownNames,
    MessageTemplate,
)


def get_flag_name(obj: ADCMEntity, msg: str = "") -> str:
    name = f"{obj} has an outdated configuration"
    if msg:
        name = f"{name}: {msg}"

    return name


def create_flag(obj: ADCMEntity, msg: str = "") -> ConcernItem:
    reason = MessageTemplate.get_message_from_template(name=KnownNames.CONFIG_FLAG.value, source=obj)
    if msg:
        reason["message"] = f"{reason['message']}: {msg}"

    return ConcernItem.objects.create(
        type=ConcernType.FLAG,
        name=get_flag_name(obj, msg),
        reason=reason,
        owner=obj,
        cause=ConcernCause.CONFIG,
        blocking=False,
    )


def remove_flag(obj: ADCMEntity, msg: str = "") -> None:
    flag = get_own_flag(owner=obj, msg=msg)
    if not flag:
        return

    flag.delete()


def get_own_flag(owner: ADCMEntity, msg: str) -> ConcernItem:
    return ConcernItem.objects.filter(
        type=ConcernType.FLAG, owner_id=owner.pk, owner_type=owner.content_type, name=get_flag_name(owner, msg)
    ).first()


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


def update_flags() -> None:
    for flag in ConcernItem.objects.filter(type=ConcernType.FLAG):
        if flag.owner is None:
            flag.delete()
            continue

        update_hierarchy(concern=flag)


def update_object_flag(obj: ADCMEntity, msg: str = "") -> None:
    if not obj.prototype.allow_flags:
        return

    flag = get_own_flag(owner=obj, msg=msg)

    if not flag:
        flag = create_flag(obj=obj, msg=msg)

    update_hierarchy(concern=flag)
