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

import pytest
# pylint: disable=W0611, W0621

from adcm_client.objects import ADCMClient

from adcm_pytest_plugin.utils import parametrize_by_data_subdirs, get_data_dir, random_string

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.locators import Common
from tests.ui_tests.app.pages import Configuration, LoginPage


@pytest.fixture()
def app(adcm_fs):
    return ADCMTest(adcm_fs)


@pytest.fixture()
def login(app):
    app.driver.get(app.adcm.url)
    login = LoginPage(app.driver)
    login.login("admin", "admin")


@parametrize_by_data_subdirs(
    __file__, "invisible_false_advanced_false")
def test_all_false(sdk_client_fs: ADCMClient, path, app, login):
    """Check RO fields with UI options as false
    Scenario:
    1. Check that field visible
    2. Check that we cannot edit field (read-only tag presented)
    3. Check that save button not active
    4. Click advanced
    5. Check that field visible
    6. Check that we cannot edit field (read-only tag presented)
    """
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    groups = config.get_field_groups()
    for group in groups:
        assert group.is_displayed(), group.get_attribute("class")
    assert not config.save_button_status()
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    groups = config.get_field_groups()
    for group in groups:
        assert group.is_displayed(), group.get_attribute("class")
    fields = config.get_app_fields()
    assert len(fields) == 1
    assert config.read_only_element(fields[0])
    form_fields = fields[0].find_elements(*Common.mat_form_field)
    for form_field in form_fields:
        assert not config.editable_element(form_field)
    assert not config.save_button_status()

@parametrize_by_data_subdirs(
    __file__, "invisible_true_advanced_true")
def test_all_true(sdk_client_fs: ADCMClient, path, app, login):
    """Check RO fields with UI options in true
    Scenario:
    1. Check that field invisible
    2. Check that save button not active
    3. Click advanced
    4. Check that field invisible
    """
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")
    assert not config.save_button_status()
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")

@parametrize_by_data_subdirs(
    __file__, "invisible_false_advanced_true")
def test_invisible_false_advanced_true(sdk_client_fs: ADCMClient, path, app, login):
    """Check RO fields with advanced true and invisible false
    Scenario:
    1. Check that field invisible
    2. Check that save button not active
    3. Click advanced
    4. Check that field visible
    5. Check that we cannot edit field (read-only tag presented)
    """
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")
    assert not config.save_button_status()
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    groups = config.get_field_groups()
    for group in groups:
        assert group.is_displayed(), group.get_attribute("class")
    assert not config.save_button_status()
    fields = config.get_app_fields()
    assert len(fields) == 1
    assert config.read_only_element(fields[0])
    form_fields = fields[0].find_elements(*Common.mat_form_field)
    for form_field in form_fields:
        assert not config.editable_element(form_field)


@parametrize_by_data_subdirs(
    __file__, "invisible_true_advanced_false")
def test_invisible_true_advanced_false(sdk_client_fs: ADCMClient, path, app, login):
    """Check RO field with invisible true and advanced false
    Scenario:
    1. Check that field invisible
    2. Check that save button not active
    3. Click advanced
    4. Check that field invisible
    """
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")
    assert not config.save_button_status()
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")


def test_save_button_status_for_required_field_with_not_active_group(
        sdk_client_fs: ADCMClient, app, login):
    """ Check save button status for cluster with RO field with
     not active activatable group and required field
    1. Create cluster
    2. Check that save button active because config not active (advanced not clicked and
    activatable option is false
    3. Click advanced
    4. Check that save button active because activatable option is false
    5. Activate group
    6. Check that save button not active because field empty but required
    7. Click advanced
    8. Check that save button is active because avanced option is false
    """
    path = get_data_dir(
        __file__, "save_button_status_for_required_field_with_not_active_group")
    bundle = sdk_client_fs.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    assert config.save_button_status()
    config.click_advanced()
    assert config.advanced
    assert config.save_button_status()
    config.activate_group_by_name(
        group_name)
    assert config.group_is_active_by_name(group_name)
    assert not config.save_button_status()
    config.click_advanced()
    assert config.save_button_status()
