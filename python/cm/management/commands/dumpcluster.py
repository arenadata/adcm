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

# pylint: disable=too-many-locals

import json

from django.core.management.base import BaseCommand

from cm import models


def serialize_datetime_fields(obj, fields=None):
    if fields is not None:
        for field in fields:
            obj[field] = obj[field].isoformat()


def get_object(model, object_id, fields, datetime_fields=None):
    obj = model.objects.values(*fields).get(id=object_id)
    serialize_datetime_fields(obj, datetime_fields)
    return obj


def get_objects(model, fields, filters, datetime_fields=None):
    objects = list(model.objects.filters(**filters).values(*fields))
    for obj in objects:
        serialize_datetime_fields(obj, datetime_fields)
    return objects


def get_bundle_hash(prototype_id):
    prototype = models.Prototype.objects.get(id=prototype_id)
    bundle = models.Bundle.objects.get(id=prototype.bundle_id)
    return bundle.hash


def get_config(object_config_id):
    fields = ('config', 'attr', 'date', 'description')
    try:
        object_config = models.ObjectConfig.objects.get(id=object_config_id)
    except models.ObjectConfig.DoesNotExist:
        return None
    config = {}
    for name in ['current', 'previous']:
        _id = getattr(object_config, name)
        if _id:
            config[name] = get_object(models.ConfigLog, _id, fields, ['date'])
        else:
            config[name] = None
    return config


def get_cluster(cluster_id):
    fields = (
        'id',
        'name',
        'description',
        'config',
        'state',
        'stack',
        'issue',
        'prototype',
    )
    cluster = get_object(models.Cluster, cluster_id, fields)
    cluster['config'] = get_config(cluster['config'])
    cluster['bundle_hash'] = get_bundle_hash(cluster.pop('prototype'))
    return cluster


def get_provider(provider_id):
    fields = (
        'id',
        'prototype',
        'name',
        'description',
        'config',
        'state',
        'stack',
        'issue',
    )
    provider = get_object(models.HostProvider, provider_id, fields)
    provider['config'] = get_config(provider['config'])
    provider['bundle_hash'] = get_bundle_hash(provider.pop('prototype'))
    return provider


def get_host(host_id):
    fields = (
        'id',
        'prototype',
        'fqdn',
        'description',
        'provider',
        'provider__name',
        'config',
        'state',
        'stack',
        'issue',
    )
    host = get_object(models.Host, host_id, fields)
    host['config'] = get_config(host['config'])
    host['bundle_hash'] = get_bundle_hash(host.pop('prototype'))
    return host


def get_service(service_id):
    fields = (
        'id',
        'prototype',
        # 'service',  # ???
        'config',
        'state',
        'stack',
        'issue',
    )
    service = get_object(models.ClusterObject, service_id, fields)
    service['config'] = get_config(service['config'])
    service['bundle_hash'] = get_bundle_hash(service.pop('prototype'))
    return service


def get_component(component_id):
    fields = (
        'id',
        'prototype',
        'service',
        'config',
        'state',
        'stack',
        'issue',
    )
    component = get_object(models.ServiceComponent, component_id, fields)
    component['config'] = get_config(component['config'])
    component['bundle_hash'] = get_bundle_hash(component.pop('prototype'))
    return component


def get_host_component(host_component_id):
    fields = (
        'cluster',
        'host',
        'service',
        'component',
        'state',
    )
    host_component = get_object(models.HostComponent, host_component_id, fields)
    return host_component


class Command(BaseCommand):
    help = 'Dump cluster object to JSON format'

    def add_arguments(self, parser):
        parser.add_argument(
            '-c', '--cluster_id', action='store', dest='cluster_id', required=True,
            type=int, help='Cluster ID'
        )
        parser.add_argument(
            '-o', '--output', help='Specifies file to which the output is written.'
        )

    def handle(self, *args, **options):
        cluster_id = options['cluster_id']
        output = options['output']
        cluster = get_cluster(cluster_id)

        data = {
            'cluster': cluster,
            'hosts': [],
            'providers': [],
            'services': [],
            'components': [],
            'host_components': [],
        }

        provider_ids = set()

        for host_obj in models.Host.objects.filter(cluster_id=cluster['id']):
            host = get_host(host_obj.id)
            provider_ids.add(host['provider'])
            data['hosts'].append(host)

        host_ids = [host['id'] for host in data['hosts']]

        for provider_obj in models.HostProvider.objects.filter(id__in=provider_ids):
            provider = get_provider(provider_obj.id)
            data['providers'].append(provider)

        for service_obj in models.ClusterObject.objects.filter(cluster_id=cluster['id']):
            service = get_service(service_obj.id)
            data['services'].append(service)

        service_ids = [service['id'] for service in data['services']]

        for component_obj in models.ServiceComponent.objects.filter(
                cluster_id=cluster['id'], service_id__in=service_ids):
            component = get_component(component_obj.id)
            data['components'].append(component)

        component_ids = [component['id'] for component in data['components']]

        for host_component_obj in models.HostComponent.objects.filter(
                cluster_id=cluster['id'], host_id__in=host_ids, service_id__in=service_ids,
                component_id__in=component_ids):
            host_component = get_host_component(host_component_obj.id)
            data['host_components'].append(host_component)

        result = json.dumps(data, indent=2)

        if output:
            with open(output, 'w') as f:
                f.write(result)
        else:
            self.stdout.write(result)
