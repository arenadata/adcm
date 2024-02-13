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

from pathlib import Path
from typing import Any

from django.conf import settings

from cm.models import (
    Action,
    Cluster,
    ClusterObject,
    Host,
    HostProvider,
    ObjectType,
    ServiceComponent,
    get_object_cluster,
)
from cm.services.job.inventory import get_adcm_configuration
from cm.services.job.types import (
    ADCMActionType,
    ClusterActionType,
    ComponentActionType,
    HostActionType,
    HostProviderActionType,
    JobConfig,
    JobData,
    JobEnv,
    Selector,
    ServiceActionType,
)
from cm.services.job.utils import JobScope, get_bundle_root, get_script_path, get_selector

IMPLEMENTED_ACTION_PROTO_TYPES = (
    ObjectType.ADCM,
    ObjectType.CLUSTER,
    ObjectType.SERVICE,
    ObjectType.COMPONENT,
    ObjectType.PROVIDER,
    ObjectType.HOST,
)
ADCM_HOSTGROUP = "127.0.0.1"


def get_job_config(job_scope: JobScope) -> dict[str, Any]:
    if (action_proto_type := job_scope.action.prototype.type) not in IMPLEMENTED_ACTION_PROTO_TYPES:
        raise NotImplementedError(f'Job Config can\'t be generated for action of "{action_proto_type}" object')

    return JobConfig(
        adcm={"config": get_adcm_configuration()},
        context=get_context(
            action=job_scope.action,
            object_type=job_scope.object.prototype.type,
            selector=get_selector(obj=job_scope.object, action=job_scope.action),
        ),
        env=JobEnv(
            run_dir=str(settings.RUN_DIR),
            log_dir=str(settings.LOG_DIR),
            tmp_dir=str(Path(settings.RUN_DIR, f"{job_scope.job_id}", "tmp")),
            stack_dir=str(Path(get_bundle_root(action=job_scope.action), job_scope.action.prototype.bundle.hash)),
            status_api_token=str(settings.STATUS_SECRET_KEY),
        ),
        job=_get_job_data(job_scope=job_scope),
    ).dict(exclude_unset=True)


def get_context(action: Action, object_type: str, selector: Selector) -> dict[str, int | str]:
    context = {f"{k}_id": v["id"] for k, v in selector.items()}
    context["type"] = object_type

    if object_type == ObjectType.HOST and action.host_action:
        context["type"] = action.prototype.type

    return context


def _get_job_data(job_scope: JobScope) -> JobData:
    cluster = get_object_cluster(obj=job_scope.object)

    job_data = JobData(
        id=job_scope.job_id,
        action=job_scope.action.name,
        job_name=job_scope.action.name,
        command=job_scope.action.name,
        script=job_scope.action.script,
        verbose=job_scope.task.verbose,
        playbook=get_script_path(action=job_scope.action, sub_action=job_scope.sub_action),
        action_type_specification=_get_action_type_specific_data(
            cluster=cluster, obj=job_scope.object, action=job_scope.action
        ),
    )

    if job_scope.action.params:
        job_data.params = job_scope.action.params

    if job_scope.sub_action:
        job_data.script = job_scope.sub_action.script
        job_data.job_name = job_scope.sub_action.name
        job_data.command = job_scope.sub_action.name
        if job_scope.sub_action.params:
            job_data.params = job_scope.sub_action.params

    if cluster is not None:
        job_data.cluster_id = cluster.pk

    if job_scope.config:
        job_data.config = job_scope.config

    return job_data


def _get_action_type_specific_data(
    cluster: Cluster, obj: ClusterObject | ServiceComponent | HostProvider | Host, action: Action
) -> (
    ClusterActionType
    | ServiceActionType
    | ComponentActionType
    | HostProviderActionType
    | HostActionType
    | ADCMActionType
):
    match action.prototype.type:
        case ObjectType.SERVICE:
            if action.host_action:
                service = ClusterObject.objects.get(prototype=action.prototype, cluster=cluster)

                return ServiceActionType(
                    action_proto_type="service",
                    hostgroup=service.name,
                    service_id=service.pk,
                    service_type_id=service.prototype_id,
                )

            return ServiceActionType(
                action_proto_type="service",
                hostgroup=obj.prototype.name,
                service_id=obj.pk,
                service_type_id=obj.prototype_id,
            )

        case ObjectType.COMPONENT:
            if action.host_action:
                service = ClusterObject.objects.get(prototype=action.prototype.parent, cluster=cluster)
                comp = ServiceComponent.objects.get(prototype=action.prototype, cluster=cluster, service=service)

                return ComponentActionType(
                    action_proto_type="component",
                    hostgroup=f"{service.name}.{comp.name}",
                    service_id=service.pk,
                    component_id=comp.pk,
                    component_type_id=comp.prototype_id,
                )

            return ComponentActionType(
                action_proto_type="component",
                hostgroup=f"{obj.service.prototype.name}.{obj.prototype.name}",
                service_id=obj.service_id,
                component_id=obj.pk,
                component_type_id=obj.prototype_id,
            )

        case ObjectType.CLUSTER:
            return ClusterActionType(action_proto_type="cluster", hostgroup=ObjectType.CLUSTER.name)

        case ObjectType.HOST:
            obj: Host
            return HostActionType(
                action_proto_type="host",
                hostgroup=ObjectType.HOST.name,
                hostname=obj.fqdn,
                host_id=obj.pk,
                host_type_id=obj.prototype_id,
                provider_id=obj.provider_id,
            )

        case ObjectType.PROVIDER:
            return HostProviderActionType(
                action_proto_type="provider",
                hostgroup=ObjectType.PROVIDER.name,
                provider_id=obj.pk,
            )

        case ObjectType.ADCM:
            return ADCMActionType(action_proto_type="adcm", hostgroup=ADCM_HOSTGROUP)
