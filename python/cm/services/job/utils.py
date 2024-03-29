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
from pathlib import Path

from core.types import ObjectID
from django.conf import settings
from django.utils.functional import cached_property
from pydantic import Json

from cm.models import (
    Action,
    ClusterObject,
    JobLog,
    ObjectType,
    ServiceComponent,
    SubAction,
    TaskLog,
)
from cm.services.job.types import Selector
from cm.services.types import ADCMEntityType


@dataclass
class JobScope:
    job_id: ObjectID
    object: ADCMEntityType

    @cached_property
    def task(self) -> TaskLog:
        return TaskLog.objects.select_related("action", "action__prototype", "action__prototype__bundle").get(
            pk=self.job.task_id
        )

    @cached_property
    def job(self) -> JobLog:
        return JobLog.objects.get(pk=self.job_id)

    @cached_property
    def hosts(self) -> Json:
        return self.task.hosts or None

    @cached_property
    def config(self) -> Json:
        return self.task.config or None

    @cached_property
    def action(self) -> Action | None:
        return self.task.action

    @cached_property
    def sub_action(self) -> SubAction | None:
        return self.job.sub_action


def get_selector(obj: ADCMEntityType, action: Action) -> Selector:
    selector: Selector = {obj.prototype.type: {"id": obj.pk, "name": obj.display_name}}

    match obj.prototype.type:
        case ObjectType.SERVICE:
            selector[ObjectType.CLUSTER.value] = {"id": obj.cluster.pk, "name": obj.cluster.display_name}

        case ObjectType.COMPONENT:
            selector[ObjectType.SERVICE.value] = {"id": obj.service.pk, "name": obj.service.display_name}
            selector[ObjectType.CLUSTER.value] = {"id": obj.cluster.pk, "name": obj.cluster.display_name}

        case ObjectType.HOST:
            if action.host_action:
                if obj.cluster_id is None:
                    raise ValueError(f'Host "{obj.fqdn}" is not bound to any cluster')

                cluster = obj.cluster
                selector[ObjectType.CLUSTER.value] = {"id": cluster.pk, "name": cluster.display_name}

                if action.prototype.type == ObjectType.SERVICE:
                    service = ClusterObject.objects.get(prototype=action.prototype, cluster=cluster)
                    selector[ObjectType.SERVICE.value] = {"id": service.pk, "name": service.display_name}

                elif action.prototype.type == ObjectType.COMPONENT:
                    service = ClusterObject.objects.get(prototype=action.prototype.parent, cluster=cluster)
                    selector[ObjectType.SERVICE.value] = {"id": service.pk, "name": service.display_name}
                    component = ServiceComponent.objects.get(
                        prototype=action.prototype, cluster=cluster, service=service
                    )
                    selector[ObjectType.COMPONENT.value] = {"id": component.pk, "name": component.display_name}

            else:
                selector[ObjectType.PROVIDER.value] = {"id": obj.provider.pk, "name": obj.provider.display_name}

    return selector


def get_script_path(action: Action, sub_action: SubAction | None) -> str:
    script = action.script
    if sub_action:
        script = sub_action.script

    relative_path_part = "./"
    if script.startswith(relative_path_part):
        script = Path(action.prototype.path, script.lstrip(relative_path_part))

    return str(Path(get_bundle_root(action=action), action.prototype.bundle.hash, script))


def get_bundle_root(action: Action) -> str:
    if action.prototype.type == "adcm":
        return str(Path(settings.BASE_DIR, "conf"))

    return str(settings.BUNDLE_DIR)
