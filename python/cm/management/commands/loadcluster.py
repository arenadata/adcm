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

from django.core.management.base import BaseCommand

from cm import models


def deserializer_datetime_fields(obj, fields=None):
    if obj is not None and fields is not None:
        for field in fields:
            obj[field] = datetime.fromisoformat(obj[field])


def fix_object(obj, fields):
    return {k: v for k, v in obj.items() if k not in fields}


def create_config(config):
    if config is not None:
        current_config = config['current']
        deserializer_datetime_fields(current_config, ['date'])
        previous_config = config['previous']
        deserializer_datetime_fields(previous_config, ['date'])

        # conf = models.ObjectConfig(current=0, previous=0)  # TEST
        conf = models.ObjectConfig.objects.create(current=0, previous=0)

        # current = models.ConfigLog(obj_ref=conf, **current_config)  # TEST
        current = models.ConfigLog.objects.create(obj_ref=conf, **current_config)
        current_id = current.id
        if previous_config is not None:
            # previous = models.ConfigLog(obj_ref=conf, **previous_config)  # TEST
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
    bundle = models.Bundle.objects.get(hash=cluster.pop('bundle_hash'))
    prototype = models.Prototype.objects.get(bundle=bundle, type='cluster')
    ex_id = cluster.pop('id')
    config = create_config(cluster.pop('config'))
    # cluster = models.Cluster(prototype=prototype, config=config, **cluster)  # TEST
    cluster = models.Cluster.objects.create(prototype=prototype, config=config, **cluster)
    return ex_id, cluster


def create_provider(provider):
    bundle = models.Bundle.objects.get(hash=provider.pop('bundle_hash'))
    prototype = models.Prototype.objects.get(bundle=bundle, type='provider')
    ex_id = provider.pop('id')
    config = create_config(provider.pop('config'))
    # provider = models.HostProvider(prototype=prototype, config=config, **provider)  # TEST
    provider = models.HostProvider.objects.create(prototype=prototype, config=config, **provider)
    return ex_id, provider


def create_host(host, cluster):
    bundle = models.Bundle.objects.get(hash=host.pop('bundle_hash'))
    prototype = models.Prototype.objects.get(bundle=bundle, type='host')
    ex_id = host.pop('id')
    host.pop('provider')
    config = create_config(host.pop('config'))
    provider = models.HostProvider.objects.get(name=host.pop('provider__name'))
    # host = models.Host(  # TEST
    #     prototype=prototype,
    #     provider=provider,
    #     config=config,
    #     cluster=cluster,
    #     **host,
    # )
    host = models.Host.objects.create(
        prototype=prototype,
        provider=provider,
        config=config,
        cluster=cluster,
        **host,
    )
    return ex_id, host


def create_service(service, cluster):
    bundle = models.Bundle.objects.get(hash=service.pop('bundle_hash'))
    prototype = models.Prototype.objects.get(bundle=bundle, type='service')
    ex_id = service.pop('id')
    config = create_config(service.pop('config'))
    # service = models.ClusterObject(  # TEST
    #     prototype=prototype,
    #     cluster=cluster,
    #     config=config,
    #     **service
    # )
    service = models.ClusterObject.objects.create(
        prototype=prototype,
        cluster=cluster,
        config=config,
        **service
    )
    return ex_id, service


def create_component(component, cluster, service):
    bundle = models.Bundle.objects.get(hash=component.pop('bundle_hash'))
    prototype = models.Prototype.objects.get(bundle=bundle, type='component')
    ex_id = component.pop('id')
    config = create_config(component.pop('config'))
    # component = models.ServiceComponent(  # TEST
    #     prototype=prototype,
    #     cluster=cluster,
    #     service=service,
    #     config=config,
    #     **component
    # )
    component = models.ServiceComponent.objects.create(
        prototype=prototype,
        cluster=cluster,
        service=service,
        config=config,
        **component
    )
    return ex_id, component


def create_host_component(host_component, cluster, host, service, component):
    host_component.pop('cluster')
    # host_component = models.HostComponent(  # TEST
    #     cluster=cluster,
    #     host=host,
    #     service=service,
    #     component=component,
    #     **host_component
    # )
    host_component = models.HostComponent.objects.create(
        cluster=cluster,
        host=host,
        service=service,
        component=component,
        **host_component
    )
    return host_component


class Command(BaseCommand):
    help = 'Load cluster object from JSON format'

    def add_arguments(self, parser):
        parser.add_argument('file_path', nargs='?')

    def handle(self, *args, **options):
        file_path = options.get('file_path')
        with open(file_path, 'r') as f:
            data = json.load(f)

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
