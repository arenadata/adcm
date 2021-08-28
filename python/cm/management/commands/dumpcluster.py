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
import sys

from django.conf import settings
from django.core.management.base import BaseCommand

from cm import models


def serialize_datetime_fields(obj, fields=None):
    """
    Modifies fields of type datetime to ISO string

    :param obj: Object in dictionary format
    :type obj: dict
    :param fields: List of fields in datetime format
    :type fields: list
    """
    if fields is not None:
        for field in fields:
            obj[field] = obj[field].isoformat()


def get_object(model, object_id, fields, datetime_fields=None):
    """
    The object is returned in dictionary format

    :param model: Type object
    :param object_id: Object ID
    :type object_id: int
    :param fields: List of fields
    :type fields: tuple
    :param datetime_fields: List of fields in datetime format
    :type datetime_fields: list
    :return: Object in dictionary format
    :rtype: dict
    """
    obj = model.objects.values(*fields).get(id=object_id)
    serialize_datetime_fields(obj, datetime_fields)
    return obj


def get_objects(model, fields, filters, datetime_fields=None):
    objects = list(model.objects.filters(**filters).values(*fields))
    for obj in objects:
        serialize_datetime_fields(obj, datetime_fields)
    return objects


def get_bundle(prototype_id):
    """
    Returns bundle object in dictionary format

    :param prototype_id: Prototype object ID
    :type prototype_id: int
    :return: Bundle object
    :rtype: dict
    """
    fields = ('name', 'version', 'edition', 'hash', 'description')
    prototype = models.Prototype.objects.get(id=prototype_id)
    bundle = get_object(models.Bundle, prototype.bundle_id, fields)
    return bundle


def get_bundle_hash(prototype_id):
    """
    Returns the hash of the bundle

    :param prototype_id: Object ID
    :type prototype_id: int
    :return: The hash of the bundle
    :rtype: str
    """
    bundle = get_bundle(prototype_id)
    return bundle['hash']


def get_config(object_config_id):
    """
    Returns current and previous config

    :param object_config_id:
    :type object_config_id: int
    :return: Current and previous config in dictionary format
    :rtype: dict
    """
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
    """
    Returns cluster object in dictionary format

    :param cluster_id: Object ID
    :type cluster_id: int
    :return: Cluster object
    :rtype: dict
    """
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
    bundle = get_bundle(cluster.pop('prototype'))
    cluster['bundle_hash'] = bundle['hash']
    return cluster, bundle


def get_provider(provider_id):
    """
    Returns provider object in dictionary format

    :param provider_id: Object ID
    :type provider_id: int
    :return: Provider object
    :rtype: dict
    """
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
    bundle = get_bundle(provider.pop('prototype'))
    provider['bundle_hash'] = bundle['hash']
    return provider, bundle


def get_host(host_id):
    """
    Returns host object in dictionary format

    :param host_id: Object ID
    :type host_id: int
    :return: Host object
    :rtype: dict
    """
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
    """
    Returns service object in dictionary format

    :param service_id: Object ID
    :type service_id: int
    :return: Service object
    :rtype: dict
    """
    fields = (
        'id',
        'prototype',
        'prototype__name',
        # 'service',  # TODO: you need to remove the field from the ClusterObject model
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
    """
    Returns component object in dictionary format

    :param component_id: Object ID
    :type component_id: int
    :return: Component object
    :rtype: dict
    """
    fields = (
        'id',
        'prototype',
        'prototype__name',
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
    """
    Returns host_component object in dictionary format

    :param host_component_id: Object ID
    :type host_component_id: int
    :return: HostComponent object
    :rtype: dict
    """
    fields = (
        'cluster',
        'host',
        'service',
        'component',
        'state',
    )
    host_component = get_object(models.HostComponent, host_component_id, fields)
    return host_component


def dump(cluster_id, output):
    """
    Saving objects to file in JSON format

    :param cluster_id: Object ID
    :type cluster_id: int
    :param output: Path to file
    :type output: str
    """
    cluster, bundle = get_cluster(cluster_id)

    data = {
        'ADCM_VERSION': settings.ADCM_VERSION,
        'bundles': {
            bundle['hash']: bundle,
        },
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
        provider, bundle = get_provider(provider_obj.id)
        data['providers'].append(provider)
        data['bundles'][bundle['hash']] = bundle

    for service_obj in models.ClusterObject.objects.filter(cluster_id=cluster['id']):
        service = get_service(service_obj.id)
        data['services'].append(service)

    service_ids = [service['id'] for service in data['services']]

    for component_obj in models.ServiceComponent.objects.filter(
        cluster_id=cluster['id'], service_id__in=service_ids
    ):
        component = get_component(component_obj.id)
        data['components'].append(component)

    component_ids = [component['id'] for component in data['components']]

    for host_component_obj in models.HostComponent.objects.filter(
        cluster_id=cluster['id'],
        host_id__in=host_ids,
        service_id__in=service_ids,
        component_id__in=component_ids,
    ):
        host_component = get_host_component(host_component_obj.id)
        data['host_components'].append(host_component)

    result = json.dumps(data, indent=2)

    if output is not None:
        with open(output, 'w', encoding='utf_8') as f:
            f.write(result)
    else:
        sys.stdout.write(result)


class Command(BaseCommand):
    """
    Command for dump cluster object to JSON format

    Example:
        manage.py dumpcluster --cluster_id 1 --output cluster.json
    """

    help = 'Dump cluster object to JSON format'

    def add_arguments(self, parser):
        """
        Parsing command line arguments
        """
        parser.add_argument(
            '-c',
            '--cluster_id',
            action='store',
            dest='cluster_id',
            required=True,
            type=int,
            help='Cluster ID',
        )
        parser.add_argument('-o', '--output', help='Specifies file to which the output is written.')

    def handle(self, *args, **options):
        """Handler method"""
        cluster_id = options['cluster_id']
        output = options['output']
        dump(cluster_id, output)
