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

from uuid import uuid4

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from cm.errors import AdcmEx
from cm.models import (
    ADCM,
    Action,
    ADCMEntity,
    Bundle,
    Cluster,
    ClusterObject,
    ConcernItem,
    ConfigLog,
    GroupConfig,
    Host,
    HostComponent,
    HostProvider,
    JobLog,
    ObjectConfig,
    Prototype,
    PrototypeConfig,
    ServiceComponent,
    TaskLog,
)


def gen_name(prefix: str):
    """Generate unique name"""
    return f"{prefix + uuid4().hex}"


def gen_bundle(name: str = "") -> Bundle:
    """Generate some bundle"""
    return Bundle.objects.create(name=name or gen_name("bundle_"), version="1.0.0")


def gen_prototype(bundle: Bundle, proto_type: str, name: str = "") -> Prototype:
    """Generate prototype of specified type from bundle"""
    return Prototype.objects.create(
        type=proto_type,
        name=name or "_".join((proto_type, bundle.name)),
        version=bundle.version,
        bundle=bundle,
    )


def gen_prototype_config(prototype: Prototype, name: str, field_type: str, **kwargs):
    """Generate prototype for config field"""
    return PrototypeConfig.objects.create(prototype=prototype, name=name, type=field_type, **kwargs)


def gen_adcm() -> ADCM:
    """Generate or return existing the only ADCM object"""
    try:
        return ADCM.objects.get(name="ADCM")
    except ADCM.DoesNotExist:
        bundle = gen_bundle()
        prototype = gen_prototype(bundle, "adcm")
        return ADCM.objects.create(name="ADCM", prototype=prototype)


def gen_cluster(
    name: str | None = None,
    bundle: Bundle = None,
    prototype: Prototype = None,
    config: ObjectConfig = None,
) -> Cluster:
    """Generate cluster from specified prototype"""
    if not prototype:
        bundle = bundle or gen_bundle()
        prototype = gen_prototype(bundle, "cluster")
    return Cluster.objects.create(
        name=name or gen_name("cluster_"),
        prototype=prototype,
        config=config,
    )


def gen_service(
    cluster: Cluster,
    bundle: Bundle = None,
    prototype: Prototype = None,
    config: ObjectConfig = None,
) -> ClusterObject:
    """Generate service of specified cluster and prototype"""
    if not prototype:
        bundle = bundle or gen_bundle()
        prototype = gen_prototype(bundle, "service")
    return ClusterObject.objects.create(
        cluster=cluster,
        prototype=prototype,
        config=config,
    )


def gen_component(
    service: ClusterObject,
    bundle: Bundle = None,
    prototype: Prototype = None,
    config: ObjectConfig = None,
) -> ServiceComponent:
    """Generate service component for specified service and prototype"""
    if not prototype:
        bundle = bundle or gen_bundle()
        prototype = gen_prototype(bundle, "component")
    return ServiceComponent.objects.create(
        cluster=service.cluster,
        service=service,
        prototype=prototype,
        config=config,
    )


def gen_provider(name: str | None = None, bundle=None, prototype=None) -> HostProvider:
    """Generate host provider for specified prototype"""
    if not prototype:
        bundle = bundle or gen_bundle()
        prototype = gen_prototype(bundle, "provider")
    return HostProvider.objects.create(
        name=name or gen_name("provider_"),
        prototype=prototype,
    )


def gen_host(provider, cluster=None, fqdn: str | None = None, bundle=None, prototype=None) -> Host:
    """Generate host for specified cluster, provider, and prototype"""
    if not prototype:
        bundle = bundle or gen_bundle()
        prototype = gen_prototype(bundle, "host")
    return Host.objects.create(
        fqdn=fqdn or gen_name("host-"),
        cluster=cluster,
        provider=provider,
        prototype=prototype,
    )


def gen_host_component(component: ServiceComponent, host: Host) -> HostComponent:
    """Generate host-component for specified host and component"""
    cluster = component.service.cluster
    if not host.cluster:
        host.cluster = cluster
        host.save()
    elif host.cluster != cluster:
        raise AdcmEx("Integrity error")
    return HostComponent.objects.create(
        host=host,
        cluster=cluster,
        service=component.service,
        component=component,
    )


def gen_concern_item(concern_type, name: str | None = None, reason=None, blocking=True, owner=None) -> ConcernItem:
    """Generate ConcernItem object"""
    reason = reason or {"message": "Test", "placeholder": {}}
    return ConcernItem.objects.create(type=concern_type, name=name, reason=reason, blocking=blocking, owner=owner)


def gen_action(name: str | None = None, bundle=None, prototype=None) -> Action:
    """Generate action from specified prototype"""
    if not prototype:
        bundle = bundle or gen_bundle()
        prototype = gen_prototype(bundle, "service")
    return Action.objects.create(
        name=name or gen_name("action_"),
        display_name=f"Test {prototype.type} action",
        prototype=prototype,
        type="task",
        script="",
        script_type="ansible",
    )


def gen_task_log(obj: ADCMEntity, action: Action = None) -> TaskLog:
    return TaskLog.objects.create(
        action=action or gen_action(),
        object_id=obj.pk,
        status="CREATED",
        task_object=obj,
        start_date=timezone.now(),
        finish_date=timezone.now(),
    )


def gen_job_log(task: TaskLog) -> JobLog:
    return JobLog.objects.create(
        task=task,
        status="CREATED",
        start_date=timezone.now(),
        finish_date=timezone.now(),
    )


def generate_hierarchy(bind_to_cluster: bool = True):
    """
    Generates hierarchy:
        cluster - service - component - host - provider
    """

    adcm = gen_adcm()
    adcm.config = gen_config()
    adcm.save()

    cluster_bundle = gen_bundle()
    provider_bundle = gen_bundle()

    cluster_pt = gen_prototype(cluster_bundle, "cluster")
    cluster = gen_cluster(prototype=cluster_pt)
    cluster.config = gen_config()
    cluster.save()

    service_pt = gen_prototype(cluster_bundle, "service")
    service = gen_service(cluster, prototype=service_pt)
    service.config = gen_config()
    service.save()

    component_pt = gen_prototype(cluster_bundle, "component")
    component = gen_component(service, prototype=component_pt)
    component.config = gen_config()
    component.save()

    provider_pt = gen_prototype(provider_bundle, "provider")
    provider = gen_provider(prototype=provider_pt)
    provider.config = gen_config()
    provider.save()

    host_pt = gen_prototype(provider_bundle, "host")
    host = gen_host(provider, cluster if bind_to_cluster else None, prototype=host_pt)
    host.config = gen_config()
    host.save()

    if bind_to_cluster:
        gen_host_component(component, host)

    return {
        "cluster": cluster,
        "service": service,
        "component": component,
        "provider": provider,
        "host": host,
    }


def gen_config(config: dict = None, attr: dict = None) -> ObjectConfig:
    """Generate config, creating `ObjectConfig` object and `ConfigLog` object"""

    if config is None:
        config = {}
    if attr is None:
        attr = {}

    object_config = ObjectConfig.objects.create(current=0, previous=0)
    config_log = ConfigLog.objects.create(obj_ref=object_config, description="init", config=config, attr=attr)
    object_config.current = config_log.id
    object_config.save()

    return object_config


def gen_group(name, object_id, model_name):
    return GroupConfig.objects.create(
        object_id=object_id,
        object_type=ContentType.objects.get(model=model_name),
        name=name,
    )
