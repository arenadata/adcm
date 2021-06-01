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
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from cm import models
from cm.errors import AdcmEx


def deserializer_datetime_fields(obj, fields=None):
    """
    Modifies fields of type ISO string to datetime type

    :param obj: Object in dictionary format
    :type obj: dict
    :param fields: List of fields in ISO string format
    :type fields: list
    """
    if obj is not None and fields is not None:
        for field in fields:
            obj[field] = datetime.fromisoformat(obj[field])


def get_prototype(**kwargs):
    """
    Returns prototype object

    :param kwargs: Parameters for finding a prototype
    :return: Prototype object
    :rtype: models.Prototype
    """
    bundle = models.Bundle.objects.get(hash=kwargs.pop('bundle_hash'))
    prototype = models.Prototype.objects.get(bundle=bundle, **kwargs)
    return prototype


def create_config(config):
    """
    Creating current ConfigLog, previous ConfigLog and ObjectConfig objects

    :param config: ConfigLog object in dictionary format
    :type config: dict
    :return: ObjectConfig object
    :rtype: models.ObjectConfig
    """
    if config is not None:
        current_config = config['current']
        deserializer_datetime_fields(current_config, ['date'])
        previous_config = config['previous']
        deserializer_datetime_fields(previous_config, ['date'])

        conf = models.ObjectConfig.objects.create(current=0, previous=0)

        current = models.ConfigLog.objects.create(obj_ref=conf, **current_config)
        current_id = current.id
        if previous_config is not None:
            previous = models.ConfigLog.objects.create(obj_ref=conf, **previous_config)
            previous_id = previous.id
        else:
            previous_id = 0

        conf.current = current_id
        conf.previous = previous_id
        conf.save()
        return conf
    else:
        return None


def create_cluster(cluster):
    """
    Creating Cluster object

    :param cluster: Cluster object in dictionary format
    :type cluster: dict
    :return: Cluster object
    :rtype: models.Cluster
    """
    prototype = get_prototype(bundle_hash=cluster.pop('bundle_hash'), type='cluster')
    ex_id = cluster.pop('id')
    config = create_config(cluster.pop('config'))
    cluster = models.Cluster.objects.create(prototype=prototype, config=config, **cluster)
    return ex_id, cluster


def create_provider(provider):
    """
    Creating HostProvider object

    :param provider: HostProvider object in dictionary format
    :type provider: dict
    :return: HostProvider object
    :rtype: models.HostProvider
    """
    prototype = get_prototype(bundle_hash=provider.pop('bundle_hash'), type='provider')
    ex_id = provider.pop('id')
    config = create_config(provider.pop('config'))
    provider = models.HostProvider.objects.create(prototype=prototype, config=config, **provider)
    return ex_id, provider


def create_host(host, cluster):
    """
    Creating Host object

    :param host: Host object in dictionary format
    :type host: dict
    :param cluster: Cluster object
    :type cluster: models.Cluster
    :return: Host object
    :rtype: models.Host
    """
    prototype = get_prototype(bundle_hash=host.pop('bundle_hash'), type='host')
    ex_id = host.pop('id')
    host.pop('provider')
    config = create_config(host.pop('config'))
    provider = models.HostProvider.objects.get(name=host.pop('provider__name'))
    host = models.Host.objects.create(
        prototype=prototype,
        provider=provider,
        config=config,
        cluster=cluster,
        **host,
    )
    return ex_id, host


def create_service(service, cluster):
    """
    Creating Service object

    :param service: ClusterObject object in dictionary format
    :type service: dict
    :param cluster: Cluster object
    :type cluster: models.Cluster
    :return: ClusterObject object
    :rtype: models.ClusterObject
    """
    prototype = get_prototype(
        bundle_hash=service.pop('bundle_hash'), type='service', name=service.pop('prototype__name')
    )
    ex_id = service.pop('id')
    config = create_config(service.pop('config'))
    service = models.ClusterObject.objects.create(
        prototype=prototype, cluster=cluster, config=config, **service
    )
    return ex_id, service


def create_component(component, cluster, service):
    """
    Creating Component object

    :param component: ServiceComponent object in dictionary format
    :type component: dict
    :param cluster: Cluster object
    :type cluster: models.Cluster
    :param service: Service object
    :type service: models.ClusterObject
    :return: Component object
    :rtype: models.ServiceComponent
    """
    prototype = get_prototype(
        bundle_hash=component.pop('bundle_hash'),
        type='component',
        name=component.pop('prototype__name'),
        parent=service.prototype,
    )
    ex_id = component.pop('id')
    config = create_config(component.pop('config'))
    component = models.ServiceComponent.objects.create(
        prototype=prototype, cluster=cluster, service=service, config=config, **component
    )
    return ex_id, component


def create_host_component(host_component, cluster, host, service, component):
    """
    Creating HostComponent object

    :param host_component: HostComponent object in dictionary format
    :type host_component: dict
    :param cluster: Cluster object
    :type cluster: models.Cluster
    :param host: Host object
    :type host: models.Host
    :param service: Service object
    :type service: models.ClusterObject
    :param component: Component object
    :type component: models.ServiceComponent
    :return: HostComponent object
    :rtype: models.HostComponent
    """
    host_component.pop('cluster')
    host_component = models.HostComponent.objects.create(
        cluster=cluster, host=host, service=service, component=component, **host_component
    )
    return host_component


def check(data):
    """
    Checking cluster load

    :param data: Data from file
    :type data: dict
    """
    if settings.ADCM_VERSION != data['ADCM_VERSION']:
        raise AdcmEx(
            'DUMP_LOAD_CLUSTER_ERROR',
            msg=(
                f'ADCM versions do not match, dump version: {data["ADCM_VERSION"]},'
                f' load version: {settings.ADCM_VERSION}'
            ),
        )

    for bundle_hash, bundle in data['bundles'].items():
        try:
            models.Bundle.objects.get(hash=bundle_hash)
        except models.Bundle.DoesNotExist as err:
            raise AdcmEx(
                'DUMP_LOAD_CLUSTER_ERROR',
                msg=f'Bundle "{bundle["name"]} {bundle["version"]}" not found',
            ) from err


@atomic
def load(file_path):
    """
    Loading and creating objects from JSON file

    :param file_path: Path to JSON file
    :type file_path: str
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError as err:
        raise AdcmEx('DUMP_LOAD_CLUSTER_ERROR') from err

    check(data)

    _, cluster = create_cluster(data['cluster'])

    for provider_data in data['providers']:
        create_provider(provider_data)

    ex_host_ids = {}
    for host_data in data['hosts']:
        ex_host_id, host = create_host(host_data, cluster)
        ex_host_ids[ex_host_id] = host

    ex_service_ids = {}
    for service_data in data['services']:
        ex_service_id, service = create_service(service_data, cluster)
        ex_service_ids[ex_service_id] = service

    ex_component_ids = {}
    for component_data in data['components']:
        ex_component_id, component = create_component(
            component_data, cluster, ex_service_ids[component_data.pop('service')]
        )
        ex_component_ids[ex_component_id] = component

    for host_component_data in data['host_components']:
        create_host_component(
            host_component_data,
            cluster,
            ex_host_ids[host_component_data.pop('host')],
            ex_service_ids[host_component_data.pop('service')],
            ex_component_ids[host_component_data.pop('component')],
        )


class Command(BaseCommand):
    """
    Command for load cluster object from JSON file

    Example:
        manage.py loadcluster cluster.json
    """

    help = 'Load cluster object from JSON format'

    def add_arguments(self, parser):
        """Parsing command line arguments"""
        parser.add_argument('file_path', nargs='?')

    def handle(self, *args, **options):
        """Handler method"""
        file_path = options.get('file_path')
        load(file_path)
