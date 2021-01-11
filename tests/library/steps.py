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
import os
import tarfile
import tempfile

import allure
from adcm_pytest_plugin import utils

from .utils import (
    get_host_by_fqdn,
    get_random_service,
    get_service_id_by_name,
    get_random_host_prototype,
    get_random_cluster_prototype
)


def _pack_bundle(bundledir):
    tempdir = tempfile.mkdtemp(prefix="test")
    tarfilename = os.path.join(tempdir, os.path.basename(bundledir) + '.tar')
    with tarfile.open(tarfilename, "w") as tar:
        for sub in os.listdir(bundledir):
            tar.add(os.path.join(bundledir, sub), arcname=sub)
        tar.close()
    return tarfilename


def upload_bundle(client, bundledir):
    try:
        if os.path.isdir(bundledir):
            archfile = _pack_bundle(bundledir)
        else:
            archfile = bundledir
        file = open(archfile, 'rb')
        client.stack.upload.create(file=file)
        client.stack.load.create(bundle_file=os.path.basename(archfile))
    finally:
        os.remove(archfile)
        os.rmdir(os.path.dirname(archfile))


def _delete_all_clusters(client):
    for cluster in client.cluster.list():
        client.cluster.delete(cluster_id=cluster['id'])


def _delete_all_hosts(client):
    for host in client.host.list():
        client.host.delete(host_id=host['id'])


def _delete_all_bundles(client):
    for bundle in client.stack.bundle.list():
        client.stack.bundle.delete(bundle_id=bundle['id'])


def wipe_data(client):
    _delete_all_hosts(client)
    _delete_all_clusters(client)
    _delete_all_bundles(client)


@allure.step('Create cluster')
def create_cluster(client):
    prototype = get_random_cluster_prototype(client)
    return client.cluster.create(prototype_id=prototype['id'], name=utils.random_string())


@allure.step('Create host {1}')
def create_host_w_default_provider(client, fqdn):
    proto = get_random_host_prototype(client)
    provider = client.provider.create(prototype_id=client.stack.provider.list()[0]['id'],
                                      name=utils.random_string())
    return client.host.create(prototype_id=proto['id'], provider_id=provider['id'], fqdn=fqdn)


@allure.step('Create hostprovider')
def create_hostprovider(client):
    return client.provider.create(name=utils.random_string(),
                                  prototype_id=client.stack.provider.list()[0]['id'])


@allure.step('Add host {1} to cluster {2}')
def add_host_to_cluster(client, host, cluster):
    client.cluster.host.create(cluster_id=cluster['id'], host_id=host['id'])
    host = client.host.read(host_id=host['id'])
    return host


def partial_update_cluster(client, cluster, name, desc=None):
    if desc is None:
        return client.cluster.partial_update(cluster_id=cluster['id'], name=name)
    else:
        return client.cluster.partial_update(cluster_id=cluster['id'], name=name, description=desc)


@allure.step('Create service {1} in cluster {0}')
def create_service_by_name(client, cluster_id, service_name):
    service_id = get_service_id_by_name(client, service_name)
    return client.cluster.service.create(cluster_id=cluster_id, prototype_id=service_id)


@allure.step('Create random service in cluster {0}')
def create_random_service(client, cluster_id):
    service = get_random_service(client)['name']
    return create_service_by_name(client, cluster_id, service)


@allure.step('Read Service with id= {0}')
def read_service(client, identifer):
    return client.stack.service.read(prototype_id=identifer)


@allure.step('Read cluster with id {0}')
def read_cluster(client, identifier):
    return client.cluster.read(cluster_id=identifier)


@allure.step('Read host with id {0}')
def read_host(client, identifier):
    return client.host.read(host_id=identifier)


@allure.step('Delete host {0}')
def delete_host(client, fqdn):
    host_id = get_host_by_fqdn(client, fqdn)['id']
    return client.host.delete(host_id=host_id)


@allure.step('Delete all clusters')
def delete_all_clusters(client):
    for cluster in client.cluster.list():
        client.cluster.delete(cluster_id=cluster['id'])


@allure.step('Delete all hosts')
def delete_all_hosts(client):
    for host in client.host.list():
        client.host.delete(host_id=host['id'])


@allure.step('Delete all hostcomponents')
def delete_all_hostcomponents(client):
    for hostcomponent in client.hostcomponent.list():
        client.hostcomponent.delete(id=hostcomponent['id'])


def delete_all_data(client):
    with allure.step('Cleaning all data'):
        # delete_all_hostcomponents()
        delete_all_clusters(client)
        delete_all_hosts(client)


@allure.step('Create hostservice in specific cluster')
def create_hostcomponent_in_cluster(client, cluster, host, service, component):
    return client.cluster.hostcomponent.create(cluster_id=cluster['id'],
                                               hc=[{"host_id": host['id'],
                                                    "service_id": service['id'],
                                                    "component_id": component['id']}])
