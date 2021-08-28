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

from cm import models


def _gen_name(prefix: str, name='name'):
    """Generate unique name"""
    return {name: prefix + uuid4().hex}


def gen_bundle(name=''):
    """Generate some bundle"""
    return models.Bundle.objects.create(**_gen_name(name), version='1.0.0')


def gen_prototype(bundle: models.Bundle, proto_type):
    """Generate prototype of specified type from bundle"""
    return models.Prototype.objects.create(
        type=proto_type,
        name=bundle.name,
        version=bundle.version,
        bundle=bundle,
    )


def gen_adcm():
    """Generate or return existing the only ADCM object"""
    try:
        return models.ADCM.objects.get(name='ADCM')
    except models.ObjectDoesNotExist:
        bundle = gen_bundle()
        prototype = gen_prototype(bundle, 'adcm')
        return models.ADCM.objects.create(name='ADCM', prototype=prototype)


def gen_cluster(name='', bundle=None, prototype=None):
    """Generate cluster from specified prototype"""
    if not prototype:
        bundle = bundle or gen_bundle()
        prototype = gen_prototype(bundle, 'cluster')
    return models.Cluster.objects.create(
        **_gen_name(name),
        prototype=prototype,
    )


def gen_service(cluster, bundle=None, prototype=None):
    """Generate service of specified cluster and prototype"""
    if not prototype:
        bundle = bundle or gen_bundle()
        prototype = gen_prototype(bundle, 'service')
    return models.ClusterObject.objects.create(
        cluster=cluster,
        prototype=prototype,
    )


def gen_component(service, bundle=None, prototype=None):
    """Generate service component for specified service and prototype"""
    if not prototype:
        bundle = bundle or gen_bundle()
        prototype = gen_prototype(bundle, 'component')
    return models.ServiceComponent.objects.create(
        cluster=service.cluster,
        service=service,
        prototype=prototype,
    )


def gen_provider(name='', bundle=None, prototype=None):
    """Generate host provider for specified prototype"""
    if not prototype:
        bundle = bundle or gen_bundle()
        prototype = gen_prototype(bundle, 'provider')
    return models.HostProvider.objects.create(
        **_gen_name(name),
        prototype=prototype,
    )


def gen_host(provider, cluster=None, fqdn='', bundle=None, prototype=None):
    """Generate host for specified cluster, provider, and prototype"""
    if not prototype:
        bundle = bundle or gen_bundle()
        prototype = gen_prototype(bundle, 'host')
    return models.Host.objects.create(
        **_gen_name(fqdn, 'fqdn'),
        cluster=cluster,
        provider=provider,
        prototype=prototype,
    )


def gen_host_component(component, host):
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
