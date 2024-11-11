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

from functools import partial

from api_v2.concern.serializers import ConcernSerializer
from core.types import CoreObjectDescriptor
from django.db.transaction import on_commit
from djangorestframework_camel_case.util import camelize

from cm.adcm_config.utils import proto_ref
from cm.converters import orm_object_to_core_type
from cm.errors import AdcmEx
from cm.hierarchy import Tree
from cm.logger import logger
from cm.models import (
    ADCMEntity,
    Cluster,
    ClusterObject,
    ConcernCause,
    ConcernItem,
    ConcernType,
    ObjectType,
    Prototype,
    ServiceComponent,
)
from cm.services.concern import create_issue, retrieve_issue
from cm.services.concern.checks import (
    cluster_mapping_has_issue_orm_version,
    object_configuration_has_issue,
    object_has_required_services_issue,
    object_imports_has_issue,
    service_requirements_has_issue,
)
from cm.status_api import send_concern_creation_event, send_concern_delete_event


def check_service_requires(cluster: Cluster, proto: Prototype) -> None:
    if not proto.requires:
        return

    for require in proto.requires:
        req_service = ClusterObject.objects.filter(prototype__name=require["service"], cluster=cluster)
        obj_prototype = Prototype.objects.filter(name=require["service"], type="service")

        if comp_name := require.get("component"):
            req_obj = ServiceComponent.objects.filter(
                prototype__name=comp_name, service=req_service.first(), cluster=cluster
            )
            obj_prototype = Prototype.objects.filter(name=comp_name, type="component", parent=obj_prototype.first())
        else:
            req_obj = req_service

        if not req_obj.exists():
            raise AdcmEx(
                code="SERVICE_CONFLICT",
                msg=f"No required {proto_ref(prototype=obj_prototype.first())} for {proto_ref(prototype=proto)}",
            )


_issue_check_map = {
    ConcernCause.CONFIG: object_configuration_has_issue,
    ConcernCause.IMPORT: object_imports_has_issue,
    ConcernCause.SERVICE: object_has_required_services_issue,
    ConcernCause.HOSTCOMPONENT: cluster_mapping_has_issue_orm_version,
    ConcernCause.REQUIREMENT: service_requirements_has_issue,
}
_prototype_issue_map = {
    ObjectType.ADCM: (ConcernCause.CONFIG,),
    ObjectType.CLUSTER: (
        ConcernCause.CONFIG,
        ConcernCause.IMPORT,
        ConcernCause.SERVICE,
        ConcernCause.HOSTCOMPONENT,
    ),
    ObjectType.SERVICE: (ConcernCause.CONFIG, ConcernCause.IMPORT, ConcernCause.REQUIREMENT),
    ObjectType.COMPONENT: (ConcernCause.CONFIG,),
    ObjectType.PROVIDER: (ConcernCause.CONFIG,),
    ObjectType.HOST: (ConcernCause.CONFIG,),
}


def add_issue_on_linked_objects(obj: ADCMEntity, issue_cause: ConcernCause) -> None:
    """Create newly discovered issue and add it to linked objects concerns"""
    object_cod = CoreObjectDescriptor(id=obj.id, type=orm_object_to_core_type(obj))
    object_own_issue = retrieve_issue(owner=object_cod, cause=issue_cause)
    issue = object_own_issue or create_issue(owner=object_cod, cause=issue_cause)

    tree = Tree(obj)
    affected_nodes = tree.get_directly_affected(node=tree.built_from)

    for node in affected_nodes:
        add_concern_to_object(object_=node.value, concern=issue)


def remove_issue(obj: ADCMEntity, issue_cause: ConcernCause) -> None:
    """Remove outdated issue from other's concerns"""
    issue = retrieve_issue(owner=CoreObjectDescriptor(id=obj.id, type=orm_object_to_core_type(obj)), cause=issue_cause)
    if not issue:
        return
    issue.delete()


def recheck_issues(obj: ADCMEntity) -> None:
    """Re-check for object's type-specific issues"""
    issue_causes = _prototype_issue_map.get(obj.prototype.type, [])
    for issue_cause in issue_causes:
        if _issue_check_map[issue_cause](obj):
            add_issue_on_linked_objects(obj=obj, issue_cause=issue_cause)
        else:
            remove_issue(obj=obj, issue_cause=issue_cause)


def update_hierarchy_issues(obj: ADCMEntity) -> None:
    """Update issues on all directly connected objects"""
    tree = Tree(obj)
    affected_nodes = tree.get_directly_affected(node=tree.built_from)
    for node in affected_nodes:
        recheck_issues(obj=node.value)


def update_issues_and_flags_after_deleting() -> None:
    """Remove issues and flags which have no owners after object deleting"""
    for concern in ConcernItem.objects.filter(type__in=(ConcernType.ISSUE, ConcernType.FLAG)):
        tree = Tree(obj=concern.owner)
        affected = {node.value for node in tree.get_directly_affected(node=tree.built_from)}
        related = set(concern.related_objects)
        if concern.owner is None:
            concern_str = str(concern)
            concern.delete()
            logger.info("Deleted %s", concern_str)
        elif related != affected:
            for object_moved_out_hierarchy in related.difference(affected):
                remove_concern_from_object(object_=object_moved_out_hierarchy, concern=concern)


def add_concern_to_object(object_: ADCMEntity, concern: ConcernItem | None) -> None:
    if not concern or getattr(concern, "id", None) is None:
        return

    if object_.concerns.filter(id=concern.id).exists():
        return

    object_.concerns.add(concern)

    concern_data = camelize(data=ConcernSerializer(instance=concern).data)
    on_commit(func=partial(send_concern_creation_event, object_=object_, concern=concern_data))


def remove_concern_from_object(object_: ADCMEntity, concern: ConcernItem | None) -> None:
    if not concern or not hasattr(concern, "id"):
        return

    concern_id = concern.id

    if not object_.concerns.filter(id=concern_id).exists():
        return

    object_.concerns.remove(concern)
    on_commit(
        func=partial(
            send_concern_delete_event, object_id=object_.pk, object_type=object_.prototype.type, concern_id=concern_id
        )
    )
