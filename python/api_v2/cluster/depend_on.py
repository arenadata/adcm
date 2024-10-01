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
from functools import reduce
from operator import or_
from typing import Iterable, TypeAlias

from cm.models import ObjectType, Prototype
from core.bundle.operations import RequiresDependencies
from core.types import ComponentName, ComponentNameKey, ObjectID, ServiceName, ServiceNameKey
from django.db.models import Q

from api_v2.prototype.utils import get_license_text

DependOnIDNameHierarchy: TypeAlias = dict[ObjectID, dict[ServiceName, set[ComponentName]]]


def prepare_depend_on_hierarchy(
    dependencies: RequiresDependencies, targets: Iterable[tuple[ObjectID, ServiceNameKey | ComponentNameKey]]
) -> DependOnIDNameHierarchy:
    result = defaultdict(lambda: defaultdict(set))

    for object_id, key in targets:
        for required_object_key in dependencies[key]:
            if isinstance(required_object_key, ComponentNameKey):
                result[object_id][required_object_key.service].add(required_object_key.component)
            elif required_object_key.service not in result[object_id]:
                result[object_id][required_object_key.service] = set()

    return result


def retrieve_serialized_depend_on_hierarchy(
    hierarchy: DependOnIDNameHierarchy, bundle_id: int, bundle_hash: str
) -> dict[ObjectID, list[dict]]:
    objects_in_hierarchy: dict[ServiceName, set[ComponentName]] = defaultdict(set)

    for object_dict in hierarchy.values():
        for service_name, component_names in object_dict.items():
            objects_in_hierarchy[service_name].update(component_names)

    service_proto_query = Q(type=ObjectType.SERVICE, name__in=objects_in_hierarchy)
    components_proto_query = reduce(
        or_,
        (
            Q(type=ObjectType.COMPONENT, name__in=component_names, parent__name=service_name)
            for service_name, component_names in objects_in_hierarchy.items()
        ),
        Q(),
    )

    serialized: dict[ServiceNameKey | ComponentNameKey, dict] = {}
    for prototype in Prototype.objects.filter(
        service_proto_query | components_proto_query, bundle_id=bundle_id
    ).select_related("parent"):
        if prototype.type == ObjectType.COMPONENT:
            key = ComponentNameKey(service=prototype.parent.name, component=prototype.name)
            serialized[key] = {
                "id": prototype.id,
                "name": prototype.name,
                "display_name": prototype.display_name,
                "version": prototype.version,
            }
            continue

        key = ServiceNameKey(service=prototype.name)
        serialized[key] = {
            "id": prototype.id,
            "name": prototype.name,
            "display_name": prototype.display_name,
            "version": prototype.version,
            "license": {
                "status": prototype.license,
                "text": get_license_text(license_path=prototype.license_path, bundle_hash=bundle_hash),
            },
        }

    return {
        object_id: [
            {
                "service_prototype": {
                    **serialized[ServiceNameKey(service=service_name)],
                    "component_prototypes": [
                        serialized[ComponentNameKey(service=service_name, component=component_name)]
                        for component_name in component_names
                    ],
                }
            }
            for service_name, component_names in dependencies.items()
        ]
        for object_id, dependencies in hierarchy.items()
    }
