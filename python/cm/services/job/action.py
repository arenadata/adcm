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

from dataclasses import dataclass, field
from functools import partial
from typing import TypeAlias

from core.job.dto import TaskPayloadDTO
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.conf import settings
from django.db.transaction import atomic, on_commit
from rbac.roles import re_apply_policy_for_jobs
from rest_framework.status import HTTP_409_CONFLICT

from cm.adcm_config.checks import check_attr
from cm.adcm_config.config import check_config_spec, get_prototype_config, process_config_spec, process_file_type
from cm.api import get_hc, save_hc
from cm.converters import model_name_to_core_type
from cm.errors import AdcmEx
from cm.models import (
    ADCM,
    Action,
    ADCMEntity,
    Cluster,
    ClusterObject,
    ConcernType,
    ConfigLog,
    Host,
    HostComponent,
    HostProvider,
    JobStatus,
    ServiceComponent,
    TaskLog,
    get_object_cluster,
)
from cm.services.config.spec import convert_to_flat_spec_from_proto_flat_spec
from cm.services.job.checks import check_constraints_for_upgrade, check_hostcomponentmap
from cm.services.job.inventory._config import update_configuration_for_inventory_inplace
from cm.services.job.prepare import prepare_task_for_action
from cm.services.job.run import run_task
from cm.status_api import send_task_status_update_event
from cm.variant import process_variant

ObjectWithAction: TypeAlias = ADCM | Cluster | ClusterObject | ServiceComponent | HostProvider | Host


@dataclass
class ActionRunPayload:
    conf: dict = field(default_factory=dict)
    attr: dict = field(default_factory=dict)
    hostcomponent: list[dict] = field(default_factory=list)
    verbose: bool = False


def run_action(
    action: Action,
    obj: ObjectWithAction,
    payload: ActionRunPayload,
) -> TaskLog:
    cluster: Cluster | None = get_object_cluster(obj=obj)

    action_target = _get_host_object(action=action, cluster=cluster) if action.host_action else obj

    object_locks = action_target.concerns.filter(type=ConcernType.LOCK)

    if action.name == settings.ADCM_DELETE_SERVICE_ACTION_NAME:
        object_locks = object_locks.exclude(owner_id=obj.id, owner_type=obj.content_type)

    if object_locks.exists():
        raise AdcmEx(code="LOCK_ERROR", msg=f"object {action_target} is locked")

    if (
        action.name not in settings.ADCM_SERVICE_ACTION_NAMES_SET
        and action_target.concerns.filter(type=ConcernType.ISSUE).exists()
    ):
        raise AdcmEx(code="ISSUE_INTEGRITY_ERROR", msg=f"object {action_target} has issues")

    if not action.allowed(obj=action_target):
        raise AdcmEx(code="TASK_ERROR", msg="action is disabled")

    spec, flat_spec = _check_action_config(action=action, obj=obj, conf=payload.conf, attr=payload.attr)

    is_upgrade_action = hasattr(action, "upgrade")

    if is_upgrade_action and not action.hostcomponentmap:
        check_constraints_for_upgrade(
            cluster=cluster, upgrade=action.upgrade, host_comp_list=_get_actual_hc(cluster=cluster)
        )

    host_map, post_upgrade_hc, delta = check_hostcomponentmap(
        cluster=cluster, action=action, new_hc=payload.hostcomponent
    )
    if action.hostcomponentmap and not (delta.get("add") or delta.get("remove")):
        # means empty delta, shouldn't be like that
        raise AdcmEx(
            code="WRONG_ACTION_HC",
            msg="Host-component is expected to be changed for this action",
            http_code=HTTP_409_CONFLICT,
        )

    with atomic():
        target = CoreObjectDescriptor(id=obj.pk, type=model_name_to_core_type(obj.__class__.__name__.lower()))
        owner = target
        if target.type == ADCMCoreType.HOST and action.host_action:
            match action.prototype_type:
                case "cluster":
                    owner = CoreObjectDescriptor(id=cluster.pk, type=ADCMCoreType.CLUSTER)
                case "service":
                    owner = CoreObjectDescriptor(
                        id=ClusterObject.objects.values_list("id", flat=True)
                        .filter(cluster=cluster, prototype_id=action.prototype_id)
                        .get(),
                        type=ADCMCoreType.SERVICE,
                    )
                case "component":
                    owner = CoreObjectDescriptor(
                        id=ServiceComponent.objects.values_list("id", flat=True)
                        .filter(cluster=cluster, prototype_id=action.prototype_id)
                        .get(),
                        type=ADCMCoreType.COMPONENT,
                    )

        task = prepare_task_for_action(
            target=target,
            owner=owner,
            action=action.pk,
            payload=TaskPayloadDTO(
                conf=payload.conf,
                attr=payload.attr,
                verbose=payload.verbose,
                hostcomponent=get_hc(cluster=cluster),
                post_upgrade_hostcomponent=post_upgrade_hc,
            ),
            delta=delta,
        )
        task_ = TaskLog.objects.get(id=task.id)
        if host_map or (is_upgrade_action and host_map is not None):
            save_hc(cluster=cluster, host_comp_list=host_map)

        if payload.conf:
            new_conf = update_configuration_for_inventory_inplace(
                configuration=payload.conf,
                attributes=payload.attr,
                specification=convert_to_flat_spec_from_proto_flat_spec(prototypes_flat_spec=flat_spec),
                config_owner=CoreObjectDescriptor(
                    id=obj.pk, type=model_name_to_core_type(model_name=obj._meta.model_name)
                ),
            )
            process_file_type(obj=task_, spec=spec, conf=payload.conf)
            task_.config = new_conf
            task_.save()

        on_commit(func=partial(send_task_status_update_event, task_id=task_.pk, status=JobStatus.CREATED.value))

    re_apply_policy_for_jobs(action_object=obj, task=task_)

    run_task(task_)

    return task_


def _get_host_object(action: Action, cluster: Cluster | None) -> ADCMEntity | None:
    obj = None
    if action.prototype.type == "service":
        obj = ClusterObject.obj.get(cluster=cluster, prototype=action.prototype)
    elif action.prototype.type == "component":
        obj = ServiceComponent.obj.get(cluster=cluster, prototype=action.prototype)
    elif action.prototype.type == "cluster":
        obj = cluster

    return obj


def _check_action_config(action: Action, obj: ADCMEntity, conf: dict, attr: dict) -> tuple[dict, dict]:
    proto = action.prototype
    spec, flat_spec, _, _ = get_prototype_config(prototype=proto, action=action, obj=obj)
    if not spec:
        if conf:
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg="Absent config in action prototype")

        return {}, {}

    if not conf:
        raise AdcmEx("TASK_ERROR", "action config is required")

    check_attr(proto, action, attr, flat_spec)

    object_config = {}
    if obj.config is not None:
        object_config = ConfigLog.objects.get(id=obj.config.current).config

    process_variant(obj=obj, spec=spec, conf=object_config)
    check_config_spec(proto=proto, obj=action, spec=spec, flat_spec=flat_spec, conf=conf, attr=attr)

    process_config_spec(obj=obj, spec=spec, new_config=conf)

    return spec, flat_spec


def _get_actual_hc(cluster: Cluster):
    new_hc = []
    for hostcomponent in HostComponent.objects.filter(cluster=cluster):
        new_hc.append((hostcomponent.service, hostcomponent.host, hostcomponent.component))
    return new_hc
