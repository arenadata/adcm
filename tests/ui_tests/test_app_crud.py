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

# Created by a1wen at 27.02.19

import os
import time

import pytest
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.docker import DockerWrapper
from selenium.common.exceptions import TimeoutException

# pylint: disable=W0611, W0621
from tests.library import steps
from tests.ui_tests.app.app import ADCMTest

DATADIR = utils.get_data_dir(__file__)
BUNDLES = os.path.join(os.path.dirname(__file__), "../stack/")


@pytest.fixture(scope="function")
def adcm(image, request):
    repo, tag = image
    dw = DockerWrapper()
    adcm = dw.run_adcm(image=repo, tag=tag, pull=False)
    adcm.api.auth(username='admin', password='admin')
    cluster_bundle = os.path.join(DATADIR, 'cluster_bundle')
    provider_bundle = os.path.join(DATADIR, 'hostprovider')
    steps.upload_bundle(adcm.api.objects, cluster_bundle)
    steps.upload_bundle(adcm.api.objects, provider_bundle)

    def fin():
        adcm.stop()

    request.addfinalizer(fin)
    return adcm


@pytest.fixture()
def app(adcm, request):
    app = ADCMTest(adcm)
    app.base_page()
    request.addfinalizer(app.destroy)
    return app


@pytest.fixture()
def cluster(app):
    return app.create_cluster()


@pytest.fixture()
def hostprovider(app):
    return app.create_provider()


@pytest.fixture()
def host(app):
    return app.create_host(utils.random_string())


@pytest.fixture()
def data(request):
    yield {'name': utils.random_string(),
           'description': utils.random_string()}


def test_run_app(app):
    app.contains_url('/login')
    app.ui.session.login('admin', 'admin')
    assert app.contains_url('/admin')


def test_cluster_creation(app, data):
    app.ui.session.login('admin', 'admin')
    app.ui.clusters.add_new_cluster(**data)
    app.ui.clusters.list_element_contains(data['name'])


def test_delete_first_cluster(app, data):
    app.ui.session.login('admin', 'admin')
    app.ui.clusters.add_new_cluster(**data)
    app.ui.clusters.delete_first_cluster()
    app.ui.clusters.list_is_empty()


def test_provider_creation(app, data):
    app.ui.session.login('admin', 'admin')
    app.ui.providers.add_new_provider(**data)
    app.ui.providers.list_element_contains(data['name'])


def test_delete_first_provider(app, data):
    app.ui.session.login('admin', 'admin')
    app.ui.providers.add_new_provider(**data)
    try:
        app.ui.providers.list_element_contains(data['name'])
    except TimeoutException:
        pytest.xfail("Flaky test")
    app.ui.providers.delete_first_provider()
    app.ui.providers.list_is_empty()


provider = data


def test_host_creation(app, provider, data):
    app.ui.session.login('admin', 'admin')
    app.ui.providers.add_new_provider(**provider)
    app.ui.hosts.add_new_host(data['name'])
    app.ui.hosts.list_element_contains(data['name'])


def test_host_creation_from_cluster_details(app, cluster, hostprovider, data):
    app.ui.session.login('admin', 'admin')
    app.ui.clusters.details.create_host_from_cluster(hostprovider, data['name'])
    app.ui.clusters.details.host_tab.list_element_contains(data['name'])


def test_host_deletion(app, provider, data):
    app.ui.session.login('admin', 'admin')
    app.ui.providers.add_new_provider(**provider)
    app.ui.hosts.add_new_host(data['name'])
    try:
        app.ui.hosts.delete_first_host()
    except TimeoutException:
        pytest.xfail("Flaky test")


def test_deletion_provider_while_it_has_host(app, provider, data):
    app.ui.session.login('admin', 'admin')
    app.ui.providers.add_new_provider(**provider)
    app.ui.hosts.add_new_host(data['name'])
    time.sleep(10)
    try:
        app.ui.providers.delete_first_provider()
        error = app.ui.providers.check_error('PROVIDER_CONFLICT')
        assert error[0], error[1]
    except (AssertionError, TimeoutException):
        pytest.xfail("Flaky test")


def test_addition_host_to_cluster(app, cluster, host):
    app.ui.session.login('admin', 'admin')
    app.ui.clusters.details.add_host_in_cluster()
    try:
        app.ui.clusters.details.host_tab.list_element_contains(host)
    except TimeoutException:
        app.ui.driver.refresh()
        app.ui.clusters.details.host_tab.list_element_contains(host)


def test_cluster_action_must_be_run(app, cluster):
    action = 'install'
    app.ui.session.login('admin', 'admin')
    app.ui.clusters.details.run_action_by_name(action)
    app.ui.jobs.check_task(action)
