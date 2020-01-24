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
import random

import coreapi
import pytest
from adcm_pytest_plugin import utils

# pylint: disable=W0611, W0621
from tests.library import steps
from tests.library.errorcodes import (
    INVALID_UPGRADE_DEFINITION, INVALID_VERSION_DEFINITION,
    UPGRADE_ERROR, UPGRADE_NOT_FOUND
)

BUNDLES = os.path.join(os.path.dirname(__file__), "stacks/")


@pytest.fixture(scope="module")
def cluster_bundles(client):
    bundle = os.path.join(BUNDLES, "cluster_bundle_before_upgrade")
    upgrade_bundle = os.path.join(BUNDLES, "upgradable_cluster_bundle")
    return bundle, upgrade_bundle


@pytest.fixture(scope="module")
def host_bundles(client):
    bundle = os.path.join(BUNDLES, "host_bundle_before_upgrade")
    upgrade_bundle = os.path.join(BUNDLES, "upgradable_host_bundle")
    return bundle, upgrade_bundle


def test_a_cluster_bundle_upgrade_will_ends_successfully(client, cluster_bundles):
    bundle, upgrade_bundle = cluster_bundles
    steps.upload_bundle(client, bundle)
    cluster = client.cluster.create(prototype_id=(client.stack.cluster.list())[0]['id'],
                                    name=__file__)
    steps.upload_bundle(client, upgrade_bundle)
    upgrade_version = random.choice(client.cluster.upgrade.list(cluster_id=cluster['id']))
    client.cluster.upgrade.do.create(cluster_id=cluster['id'], upgrade_id=upgrade_version['id'])
    result = client.cluster.read(cluster_id=cluster['id'])
    assert result['state'] == upgrade_version['state_on_success']
    steps.wipe_data(client)


def test_shouldnt_upgrade_upgrated_cluster(client, cluster_bundles):
    bundle, upgrade_bundle = cluster_bundles
    steps.upload_bundle(client, bundle)
    cluster = client.cluster.create(prototype_id=random.choice(client.stack.cluster.list())['id'],
                                    name=__file__)
    steps.upload_bundle(client, upgrade_bundle)
    upgrade_version = random.choice(client.cluster.upgrade.list(cluster_id=cluster['id']))
    client.cluster.upgrade.do.create(cluster_id=cluster['id'], upgrade_id=upgrade_version['id'])
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        client.cluster.upgrade.do.create(cluster_id=cluster['id'], upgrade_id=upgrade_version['id'])
    UPGRADE_ERROR.equal(e, 'cluster version', 'is more than upgrade max version')
    steps.wipe_data(client)


@pytest.mark.skip(reason="Test must be changed for provider's upgrade procedure")
def test_a_host_bundle_upgrade_will_ends_successfully(client, host_bundles):
    bundle, upgrade_bundle = host_bundles
    steps.upload_bundle(client, bundle)
    host = client.host.create(prototype_id=client.stack.host.list()[0]['id'], fqdn='localhost')
    steps.upload_bundle(client, upgrade_bundle)
    upgrade_version = client.host.upgrade.list(host_id=host['id'])[0]
    client.host.upgrade.do.create(upgrade_id=upgrade_version['id'], host_id=host['id'])
    result = client.host.read(host_id=host['id'])
    assert result['state'] == upgrade_version['state_on_success']
    steps.wipe_data(client)


@pytest.mark.skip(reason="Test must be changed for provider's upgrade procedure")
def test_shouldnt_upgrade_upgrated_host(client, host_bundles):
    bundle, upgrade_bundle = host_bundles
    steps.upload_bundle(client, bundle)
    host = client.host.create(prototype_id=client.stack.host.list()[0]['id'], fqdn='localhost')
    steps.upload_bundle(client, upgrade_bundle)
    upgrade_version = client.host.upgrade.list(host_id=host['id'])[0]
    client.host.upgrade.do.create(upgrade_id=upgrade_version['id'], host_id=host['id'])
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        client.host.upgrade.do.create(upgrade_id=upgrade_version['id'], host_id=host['id'])
    UPGRADE_ERROR.equal(e)
    assert 'host version' in e.value.error['desc']
    assert 'is more than upgrade max version' in e.value.error['desc']
    steps.wipe_data(client)


def test_that_check_nonexistent_cluster_upgrade(client, cluster_bundles):
    bundle, _ = cluster_bundles
    steps.upload_bundle(client, bundle)
    cluster = client.cluster.create(prototype_id=client.stack.cluster.list()[0]['id'],
                                    name=__file__)
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        client.cluster.upgrade.do.create(upgrade_id=random.randint(50, 99),
                                         cluster_id=cluster['id'])
    UPGRADE_NOT_FOUND.equal(e, 'upgrade is not found')
    steps.wipe_data(client)


@pytest.mark.skip(reason="Test must be changed for provider's upgrade procedure")
def test_that_check_nonexistent_host_upgrade(client, host_bundles):
    bundle, _ = host_bundles
    steps.upload_bundle(client, bundle)
    host = client.host.create(prototype_id=client.stack.host.list()[0]['id'], fqdn='localhost')
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        client.host.upgrade.do.create(upgrade_id=random.randint(50, 99), host_id=host['id'])
    UPGRADE_NOT_FOUND.equal(e, 'upgrade is not found')
    steps.wipe_data(client)


def test_upgrade_cluster_without_old_config(client):
    bundledir = os.path.join(BUNDLES, 'cluster_without_old_config')
    steps.upload_bundle(client, os.path.join(bundledir, 'old'))
    cluster = client.cluster.create(prototype_id=client.stack.cluster.list()[0]['id'],
                                    name=utils.random_string())
    steps.upload_bundle(client, os.path.join(bundledir, 'upgrade'))
    client.cluster.upgrade.do.create(
        upgrade_id=client.cluster.upgrade.list(cluster_id=cluster['id'])[0]['id'],
        cluster_id=cluster['id'])
    assert client.stack.cluster.read(
        prototype_id=client.cluster.read(
            cluster_id=cluster['id'])['prototype_id'])['version'] == '2-config'
    steps.wipe_data(client)


@pytest.mark.parametrize("boundary, expected", [
    ("min_cluster", "can not be used simultaneously"),
    ("max_cluster", "should be present"),
    ("min_hostprovider", "can not be used simultaneously"),
    ("max_hostprovider", "can not be used simultaneously")
])
def test_upgrade_contains_strict_and_nonstrict_value(client, boundary, expected):
    bundledir = os.path.join(BUNDLES, 'strict_and_non_strict_upgrade/' + boundary)
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, bundledir)
    INVALID_VERSION_DEFINITION.equal(e, expected, 'should be present')
