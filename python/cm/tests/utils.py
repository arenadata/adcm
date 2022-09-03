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

from django.utils import timezone

from cm import models


def _gen_name(prefix: str, name='name'):
    """Generate unique name"""
    return {name: prefix + uuid4().hex}


def gen_bundle(name='') -> models.Bundle:
    """Generate some bundle"""
    return models.Bundle.objects.create(**_gen_name(name or 'bundle_'), version='1.0.0')


def gen_prototype(bundle: models.Bundle, proto_type) -> models.Prototype:
    """Generate prototype of specified type from bundle"""
    return models.Prototype.objects.create(
        type=proto_type,
        name='_'.join((proto_type, bundle.name)),
        version=bundle.version,
        bundle=bundle,
    )


def gen_prototype_config(prototype: models.Prototype, name: str, field_type: str, **kwargs):
    """Generate prototype for config field"""
    return models.PrototypeConfig.objects.create(
        prototype=prototype, name=name, type=field_type, **kwargs
    )


def gen_adcm() -> models.ADCM:
    """Generate or return existing the only ADCM object"""
    try:
        return models.ADCM.objects.get(name='ADCM')
    except models.ObjectDoesNotExist:
        bundle = gen_bundle()
        prototype = gen_prototype(bundle, 'adcm')
        return models.ADCM.objects.create(name='ADCM', prototype=prototype)


def gen_cluster(name='', bundle=None, prototype=None) -> models.Cluster:
    """Generate cluster from specified prototype"""
    if not prototype:
        bundle = bundle or gen_bundle()
        prototype = gen_prototype(bundle, 'cluster')
    return models.Cluster.objects.create(
        **_gen_name(name or 'cluster_'),
        prototype=prototype,
    )


def gen_service(cluster, bundle=None, prototype=None) -> models.ClusterObject:
    """Generate service of specified cluster and prototype"""
    if not prototype:
        bundle = bundle or gen_bundle()
        prototype = gen_prototype(bundle, 'service')
    return models.ClusterObject.objects.create(
        cluster=cluster,
        prototype=prototype,
    )


def gen_component(service, bundle=None, prototype=None) -> models.ServiceComponent:
    """Generate service component for specified service and prototype"""
    if not prototype:
        bundle = bundle or gen_bundle()
        prototype = gen_prototype(bundle, 'component')
    return models.ServiceComponent.objects.create(
        cluster=service.cluster,
        service=service,
        prototype=prototype,
    )


def gen_provider(name='', bundle=None, prototype=None) -> models.HostProvider:
    """Generate host provider for specified prototype"""
    if not prototype:
        bundle = bundle or gen_bundle()
        prototype = gen_prototype(bundle, 'provider')
    return models.HostProvider.objects.create(
        **_gen_name(name or 'provider_'),
        prototype=prototype,
    )


def gen_host(provider, cluster=None, fqdn='', bundle=None, prototype=None) -> models.Host:
    """Generate host for specified cluster, provider, and prototype"""
    if not prototype:
        bundle = bundle or gen_bundle()
        prototype = gen_prototype(bundle, 'host')
    return models.Host.objects.create(
        **_gen_name(fqdn or 'host-', 'fqdn'),
        cluster=cluster,
        provider=provider,
        prototype=prototype,
    )


def gen_host_component(component, host) -> models.HostComponent:
    """Generate host-component for specified host and component"""
    cluster = component.service.cluster
    if not host.cluster:
        host.cluster = cluster
        host.save()
    elif host.cluster != cluster:
        raise models.AdcmEx('Integrity error')
    return models.HostComponent.objects.create(
        host=host,
        cluster=cluster,
        service=component.service,
        component=component,
    )


def gen_concern_item(
    concern_type, name=None, reason=None, blocking=True, owner=None
) -> models.ConcernItem:
    """Generate ConcernItem object"""
    reason = reason or {'message': 'Test', 'placeholder': {}}
    return models.ConcernItem.objects.create(
        type=concern_type, name=name, reason=reason, blocking=blocking, owner=owner
    )


def gen_action(name='', bundle=None, prototype=None) -> models.Action:
    """Generate action from specified prototype"""
    if not prototype:
        bundle = bundle or gen_bundle()
        prototype = gen_prototype(bundle, 'service')
    return models.Action.objects.create(
        **_gen_name(name or 'action_'),
        display_name=f'Test {prototype.type} action',
        prototype=prototype,
        type='task',
        script='',
        script_type='ansible',
    )


def gen_task_log(obj: models.ADCMEntity, action: models.Action = None) -> models.TaskLog:
    return models.TaskLog.objects.create(
        action=action or gen_action(),
        object_id=obj.pk,
        status='CREATED',
        task_object=obj,
        start_date=timezone.now(),
        finish_date=timezone.now(),
    )


def gen_job_log(task) -> models.JobLog:
    return models.JobLog.objects.create(
        task=task,
        action=task.action,
        status='CREATED',
        start_date=timezone.now(),
        finish_date=timezone.now(),
    )


def generate_hierarchy():  # pylint: disable=too-many-locals,too-many-statements
    """
    Generates hierarchy:
        cluster - service - component - host - provider
    """
    adcm = gen_adcm()
    adcm.config = gen_config()
    adcm.save()

    cluster_bundle = gen_bundle()
    provider_bundle = gen_bundle()

    cluster_pt = gen_prototype(cluster_bundle, 'cluster')
    cluster = gen_cluster(prototype=cluster_pt)
    cluster.config = gen_config()
    cluster.save()

    service_pt = gen_prototype(cluster_bundle, 'service')
    service = gen_service(cluster, prototype=service_pt)
    service.config = gen_config()
    service.save()

    component_pt = gen_prototype(cluster_bundle, 'component')
    component = gen_component(service, prototype=component_pt)
    component.config = gen_config()
    component.save()

    provider_pt = gen_prototype(provider_bundle, 'provider')
    provider = gen_provider(prototype=provider_pt)
    provider.config = gen_config()
    provider.save()

    host_pt = gen_prototype(provider_bundle, 'host')
    host = gen_host(provider, cluster, prototype=host_pt)
    host.config = gen_config()
    host.save()

    gen_host_component(component, host)

    return dict(
        cluster=cluster,
        service=service,
        component=component,
        provider=provider,
        host=host,
    )


def gen_config(config: dict = None, attr: dict = None):
    """Generate config, creating `ObjectConfig` object and `ConfigLog` object"""
    if config is None:
        config = {}
    if attr is None:
        attr = {}
    oc = models.ObjectConfig.objects.create(current=0, previous=0)
    cl = models.ConfigLog.objects.create(obj_ref=oc, description='init', config=config, attr=attr)
    oc.current = cl.id
    oc.save()
    return oc
