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

from typing import Literal

from ansible.errors import AnsibleActionFail, AnsibleError
from cm.models import ClusterObject, Host, MaintenanceMode, ServiceComponent
from pydantic import BaseModel, ValidationError

from ansible_plugin.utils import get_object_id_from_context

TYPE_CLASS_MAP = {
    "host": Host,
    "service": ClusterObject,
    "component": ServiceComponent,
}


class TaskArgs(BaseModel):
    type: Literal["host", "service", "component"]
    value: bool

    class Config:
        frozen = True


def validate_args(task_args: dict) -> AnsibleActionFail | None:
    try:
        TaskArgs(**task_args)
    except ValidationError as e:
        return AnsibleActionFail(str(e))


def validate_obj(obj: Host | ClusterObject | ServiceComponent) -> AnsibleActionFail | None:
    if obj.maintenance_mode != MaintenanceMode.CHANGING:
        return AnsibleActionFail(f'Only "{MaintenanceMode.CHANGING}" state of object maintenance mode can be changed')


def get_object(
    task_vars: dict, obj_type: Literal["host", "service", "component"]
) -> tuple[Host | ClusterObject | ServiceComponent | None, None | AnsibleError]:
    context_type = obj_type
    if obj_type == "host":
        context_type = "cluster"

    obj_pk, error = get_object_id_from_context(
        task_vars=task_vars,
        id_type=f"{obj_type}_id",
        context_types=(context_type,),
        err_msg=f'You can change "{obj_type}" maintenance mode only in {context_type} context',
        raise_=False,
    )
    if error:
        return None, error

    obj_qs = TYPE_CLASS_MAP[obj_type].objects.filter(pk=obj_pk)

    if obj_qs.exists():
        return obj_qs.get(), None

    return None, AnsibleActionFail(f'Object of type "{obj_type}" with PK "{obj_pk}" does not exist')
