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

from collections import deque
from operator import attrgetter
from typing import Iterable, TypeAlias

from core.types import ConfigID, ObjectID

from cm.models import (
    Cluster,
    ClusterObject,
    Host,
    HostProvider,
    ObjectConfig,
    ServiceComponent,
)
from cm.services.config import retrieve_config_attr_pairs
from cm.services.config.spec import FlatSpec, retrieve_flat_spec_for_objects

ObjectWithConfig: TypeAlias = Cluster | ClusterObject | ServiceComponent | HostProvider | Host
HasIssue: TypeAlias = bool


def object_configuration_has_issue(target: ObjectWithConfig) -> HasIssue:
    config_spec = next(iter(retrieve_flat_spec_for_objects(prototypes=(target.prototype_id,)).values()), None)
    if not config_spec:
        return False

    return target.id in filter_objects_with_configuration_issues(config_spec, target)


def filter_objects_with_configuration_issues(config_spec: FlatSpec, *objects: ObjectWithConfig) -> Iterable[ObjectID]:
    required_fields = tuple(name for name, spec in config_spec.items() if spec.required and spec.type != "group")
    if not required_fields:
        return ()

    object_config_log_map: dict[int, ConfigID] = dict(
        ObjectConfig.objects.values_list("id", "current").filter(id__in=map(attrgetter("config_id"), objects))
    )
    config_pairs = retrieve_config_attr_pairs(configurations=object_config_log_map.values())

    objects_with_issues: deque[ObjectID] = deque()
    for object_ in objects:
        config, attr = config_pairs[object_config_log_map[object_.config_id]]

        for composite_name in required_fields:
            group_name, field_name, *_ = composite_name.split("/")
            if not field_name:
                field_name = group_name
                group_name = None

            if group_name:
                if not attr.get(group_name, {}).get("active", False):
                    continue

                if config[group_name][field_name] is None:
                    objects_with_issues.append(object_.id)
                    break

            elif config[field_name] is None:
                objects_with_issues.append(object_.id)
                break

    return objects_with_issues
