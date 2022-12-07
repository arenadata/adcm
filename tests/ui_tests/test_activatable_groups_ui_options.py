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
# pylint: disable=redefined-outer-name,too-many-public-methods

"""Tests for activatable groups"""

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster
from adcm_pytest_plugin.utils import parametrize_by_data_subdirs, random_string
from tests.ui_tests.app.page.cluster.page import ClusterConfigPage

pytestmark = [pytest.mark.usefixtures("_login_to_adcm_over_api")]


# !===== Fixtures =====!


@pytest.fixture()
def create_cluster_and_open_config_page(sdk_client_fs: ADCMClient, path, app_fs) -> ClusterConfigPage:
    """Create cluster with config and open config page in it"""

    cluster = prepare_cluster(sdk_client_fs, path)
    config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, cluster.cluster_id)
    config_page.open()
    return config_page


# !===== FUNCS =====!


@allure.step("Prepare cluster")
def prepare_cluster(sdk_client: ADCMClient, path) -> Cluster:
    """Create cluster"""

    bundle = sdk_client.upload_from_fs(path)
    cluster = bundle.cluster_create(name=f"Test cluster {random_string()}")
    return cluster


# !===== Tests =====!


class TestActivatableGroupConfigs:
    """Tests for activatable configs in cluster"""

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_false_invisible_false_field_advanced_true_invisible_true_activiatable_false",
    )
    def test_group_advanced_false_invisible_false_field_advanced_true_invisible_true_active_false(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        path,
        app_fs,
    ):
        """Check that field is invisible if group is active or not."""

        config_page = create_cluster_and_open_config_page
        group_name = path.split("/")[-1]
        config_page.config.check_group_is_active(group_name=group_name, is_active=False)
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=False,
            is_subs_visible=False,
        )
        config_page.config.click_on_advanced()
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=True,
            is_subs_visible=False,
        )

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_false_invisible_false_field_advanced_false_invisible_true_activiatable_false",
    )
    def test_group_advanced_false_invisible_false_field_advanced_false_invisible_true_active_false(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        path,
        app_fs,
    ):
        """Check that field is invisible if group is active or not."""

        config_page = create_cluster_and_open_config_page
        group_name = path.split("/")[-1]
        config_page.config.check_group_is_active(group_name=group_name, is_active=False)
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=False,
            is_subs_visible=False,
        )
        config_page.config.click_on_advanced()
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=True,
            is_subs_visible=False,
        )

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_false_invisible_false_field_advanced_false_invisible_true_activiatable_true",
    )
    def test_group_advanced_false_invisible_false_field_advanced_false_invisible_true_active_true(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        path,
        app_fs,
    ):
        """Check that field invisible if activatable group active and not."""

        config_page = create_cluster_and_open_config_page
        group_name = path.split("/")[-1]
        config_page.config.check_group_is_active(group_name=group_name)
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=False,
            is_subs_visible=False,
        )
        config_page.config.click_on_advanced()
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=True,
            is_subs_visible=False,
        )

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_false_invisible_false_field_advanced_true_invisible_true_activiatable_true",
    )
    def test_group_advanced_false_invisible_false_field_advanced_true_invisible_true_active_true(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        path,
        app_fs,
    ):
        """Check that field invisible if activatable group active and not."""

        config_page = create_cluster_and_open_config_page
        group_name = path.split("/")[-1]
        config_page.config.check_group_is_active(group_name=group_name)
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=False,
            is_subs_visible=False,
        )
        config_page.config.click_on_advanced()
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=True,
            is_subs_visible=False,
        )

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_true_invisible_false_field_advanced_false_invisible_false_activiatable_false",
    )
    def test_group_advanced_true_invisible_false_field_advanced_false_invisible_false_active_false(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        path,
        app_fs,
    ):
        """Field visible if advanced and activatable true."""

        config_page = create_cluster_and_open_config_page
        group_name = path.split("/")[-1]
        config_page.config.check_no_rows_or_groups_on_page()
        with config_page.config.wait_config_groups_change():
            config_page.config.click_on_advanced()
        config_page.config.check_group_is_active(group_name=group_name, is_active=False)
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=False,
            is_subs_visible=False,
        )
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=True,
            is_subs_visible=True,
        )

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_true_invisible_false_field_advanced_false_invisible_false_activiatable_true",
    )
    def test_group_advanced_true_invisible_false_field_advanced_false_invisible_false_active_true(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        path,
        app_fs,
    ):
        """Field visible if advanced and activatable true."""

        config_page = create_cluster_and_open_config_page
        group_name = path.split("/")[-1]
        config_page.config.check_no_rows_or_groups_on_page()
        with config_page.config.wait_config_groups_change():
            config_page.config.click_on_advanced()
        config_page.config.check_group_is_active(group_name=group_name)
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=False,
            is_subs_visible=False,
        )
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=True,
            is_subs_visible=True,
        )

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_false_invisible_true_field_advanced_false_invisible_false_activiatable_false",
    )
    def test_group_advanced_false_invisible_true_field_advanced_false_invisible_false_active_false(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        app_fs,
    ):
        """Check that all fields and groups invisible."""

        create_cluster_and_open_config_page.config.check_no_rows_or_groups_on_page_with_advanced()

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_false_invisible_true_field_advanced_false_invisible_false_activiatable_true",
    )
    def test_group_advanced_false_invisible_true_field_advanced_false_invisible_false_active_true(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        app_fs,
    ):
        """Check that all fields and groups invisible."""

        create_cluster_and_open_config_page.config.check_no_rows_or_groups_on_page_with_advanced()

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_false_invisible_true_field_advanced_false_invisible_true_activiatable_false",
    )
    def test_group_advanced_false_invisible_true_field_advanced_false_invisible_true_active_false(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        app_fs,
    ):
        """Check that all fields and groups invisible."""

        create_cluster_and_open_config_page.config.check_no_rows_or_groups_on_page_with_advanced()

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_false_invisible_true_field_advanced_false_invisible_true_activiatable_true",
    )
    def test_group_advanced_false_invisible_true_field_advanced_false_invisible_true_active_true(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        app_fs,
    ):
        """Check that all fields and groups invisible."""

        create_cluster_and_open_config_page.config.check_no_rows_or_groups_on_page_with_advanced()

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_false_invisible_true_field_advanced_true_invisible_false_activiatable_false",
    )
    def test_group_advanced_false_invisible_true_field_advanced_true_invisible_false_active_false(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        app_fs,
    ):
        """Check that all fields and groups invisible."""

        create_cluster_and_open_config_page.config.check_no_rows_or_groups_on_page_with_advanced()

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_false_invisible_true_field_advanced_true_invisible_false_activiatable_true",
    )
    def test_group_advanced_false_invisible_true_field_advanced_true_invisible_false_active_true(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        app_fs,
    ):
        """Check that all fields and groups invisible."""

        create_cluster_and_open_config_page.config.check_no_rows_or_groups_on_page_with_advanced()

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_false_invisible_true_field_advanced_true_invisible_true_activiatable_false",
    )
    def test_group_advanced_false_invisible_true_field_advanced_true_invisible_true_active_false(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        app_fs,
    ):
        """Check that all fields and groups invisible."""

        create_cluster_and_open_config_page.config.check_no_rows_or_groups_on_page_with_advanced()

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_false_invisible_true_field_advanced_true_invisible_true_activiatable_true",
    )
    def test_group_advanced_false_invisible_true_field_advanced_true_invisible_true_active_true(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        app_fs,
    ):
        """Check that all fields and groups invisible."""

        create_cluster_and_open_config_page.config.check_no_rows_or_groups_on_page_with_advanced()

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_true_invisible_true_field_advanced_false_invisible_false_activiatable_false",
    )
    def test_group_advanced_true_invisible_true_field_advanced_false_invisible_false_active_false(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        app_fs,
    ):
        """Check that all fields and groups invisible.."""

        create_cluster_and_open_config_page.config.check_no_rows_or_groups_on_page_with_advanced()

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_true_invisible_true_field_advanced_false_invisible_false_activiatable_true",
    )
    def test_group_advanced_true_invisible_true_field_advanced_false_invisible_false_active_true(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        app_fs,
    ):
        """Check that all fields and groups invisible."""

        create_cluster_and_open_config_page.config.check_no_rows_or_groups_on_page_with_advanced()

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_true_invisible_true_field_advanced_false_invisible_true_activiatable_false",
    )
    def test_group_advanced_true_invisible_true_field_advanced_false_invisible_true_active_false(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        app_fs,
    ):
        """Check that all fields and groups invisible."""

        create_cluster_and_open_config_page.config.check_no_rows_or_groups_on_page_with_advanced()

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_true_invisible_true_field_advanced_true_invisible_false_activiatable_false",
    )
    def test_group_advanced_true_invisible_true_field_advanced_true_invisible_false_active_false(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        app_fs,
    ):
        """Check that all fields and groups invisible."""

        create_cluster_and_open_config_page.config.check_no_rows_or_groups_on_page_with_advanced()

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_true_invisible_true_field_advanced_false_invisible_true_activiatable_true",
    )
    def test_group_advanced_true_invisible_true_field_advanced_false_invisible_true_active_true(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        app_fs,
    ):
        """Check that all fields and groups invisible."""

        create_cluster_and_open_config_page.config.check_no_rows_or_groups_on_page_with_advanced()

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_true_invisible_true_field_advanced_true_invisible_false_activiatable_true",
    )
    def test_group_advanced_true_invisible_true_field_advanced_true_invisible_false_active_true(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        app_fs,
    ):
        """Check that all fields and groups invisible."""

        create_cluster_and_open_config_page.config.check_no_rows_or_groups_on_page_with_advanced()

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_true_invisible_true_field_advanced_true_invisible_true_activiatable_false",
    )
    def test_group_advanced_true_invisible_true_field_advanced_true_invisible_true_active_false(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        app_fs,
    ):
        """Check that all fields and groups invisible."""

        create_cluster_and_open_config_page.config.check_no_rows_or_groups_on_page_with_advanced()

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_true_invisible_true_field_advanced_true_invisible_true_activiatable_true",
    )
    def test_group_advanced_true_invisible_true_field_advanced_true_invisible_true_active_true(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        app_fs,
    ):
        """Check that all fields and groups invisible."""

        create_cluster_and_open_config_page.config.check_no_rows_or_groups_on_page_with_advanced()

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_true_invisible_false_field_advanced_false_invisible_true_activiatable_true",
    )
    def test_group_advanced_true_invisible_false_field_advanced_false_invisible_true_active_true(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        path,
        app_fs,
    ):
        """Check that field invisible."""

        config_page = create_cluster_and_open_config_page
        group_name = path.split("/")[-1]
        config_page.config.check_no_rows_or_groups_on_page()
        with config_page.config.wait_config_groups_change():
            config_page.config.click_on_advanced()
        config_page.config.check_group_is_active(group_name=group_name)
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=False,
            is_subs_visible=False,
        )
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=True,
            is_subs_visible=False,
        )

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_true_invisible_false_field_advanced_true_invisible_true_activiatable_true",
    )
    def test_group_advanced_true_invisible_false_field_advanced_true_invisible_true_active_true(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        path,
        app_fs,
    ):
        """Check that field invisible."""

        config_page = create_cluster_and_open_config_page
        group_name = path.split("/")[-1]
        config_page.config.check_no_rows_or_groups_on_page()
        with config_page.config.wait_config_groups_change():
            config_page.config.click_on_advanced()
        config_page.config.check_group_is_active(group_name=group_name)
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=False,
            is_subs_visible=False,
        )
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=True,
            is_subs_visible=False,
        )

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_false_invisible_false_field_advanced_false_invisible_false_activiatable_false",
    )
    def test_group_advanced_false_invisible_false_field_advanced_false_invisible_false_active_false(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        path,
        app_fs,
    ):
        """Check that group not active and field is invisible until group is not active."""

        config_page = create_cluster_and_open_config_page
        group_name = path.split("/")[-1]
        config_page.config.check_group_is_active(group_name=group_name, is_active=False)
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=False,
            is_subs_visible=False,
        )
        config_page.config.click_on_advanced()
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=True,
            is_subs_visible=True,
        )

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_false_invisible_false_field_advanced_false_invisible_false_activiatable_true",
    )
    def test_group_advanced_false_invisible_false_field_advanced_false_invisible_false_active_true(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        path,
        app_fs,
    ):
        """Check that group active and all fields always visible."""

        config_page = create_cluster_and_open_config_page
        group_name = path.split("/")[-1]
        config_page.config.check_group_is_active(group_name=group_name)
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=False,
            is_subs_visible=False,
        )
        config_page.config.click_on_advanced()
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=True,
            is_subs_visible=True,
        )

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_false_invisible_false_field_advanced_true_invisible_false_activiatable_false",
    )
    def test_group_advanced_false_invisible_false_field_advanced_true_invisible_false_active_false(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        path,
        app_fs,
    ):
        """Check that field visible if advanced group is enabled."""

        config_page = create_cluster_and_open_config_page
        group_name = path.split("/")[-1]
        config_page.config.check_group_is_active(group_name=group_name, is_active=False)
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=False,
            is_subs_visible=False,
        )
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=True,
            is_subs_visible=False,
        )
        config_page.config.click_on_advanced()
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=True,
            is_subs_visible=True,
        )

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_false_invisible_false_field_advanced_true_invisible_false_activiatable_true",
    )
    def test_group_advanced_false_invisible_false_field_advanced_true_invisible_false_active_true(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        path,
        app_fs,
    ):
        """Check that field is visible if group active and advanced enabled."""

        config_page = create_cluster_and_open_config_page
        group_name = path.split("/")[-1]
        config_page.config.check_group_is_active(group_name=group_name)
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=False,
            is_subs_visible=False,
        )
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=True,
            is_subs_visible=False,
        )
        config_page.config.click_on_advanced()
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=True,
            is_subs_visible=True,
        )

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_true_invisible_false_field_advanced_false_invisible_true_activiatable_false",
    )
    def test_group_advanced_true_invisible_false_field_advanced_false_invisible_true_active_false(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        path,
        app_fs,
    ):
        """Field invisible, group visible if advanced."""

        config_page = create_cluster_and_open_config_page
        group_name = path.split("/")[-1]
        config_page.config.check_no_rows_or_groups_on_page()
        with config_page.config.wait_config_groups_change():
            config_page.config.click_on_advanced()
        config_page.config.check_group_is_active(group_name=group_name, is_active=False)
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=False,
            is_subs_visible=False,
        )
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=True,
            is_subs_visible=False,
        )

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_true_invisible_false_field_advanced_true_invisible_false_activiatable_false",
    )
    def test_group_advanced_true_invisible_false_field_advanced_true_invisible_false_active_false(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        path,
        app_fs,
    ):
        """Check that field and group visible if advanced button clicked."""

        config_page = create_cluster_and_open_config_page
        group_name = path.split("/")[-1]
        config_page.config.check_no_rows_or_groups_on_page()
        with config_page.config.wait_config_groups_change():
            config_page.config.click_on_advanced()
        config_page.config.check_group_is_active(group_name=group_name, is_active=False)
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=False,
            is_subs_visible=False,
        )
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=True,
            is_subs_visible=True,
        )

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_true_invisible_false_field_advanced_true_invisible_false_activiatable_true",
    )
    def test_group_advanced_true_invisible_false_field_advanced_true_invisible_false_active_true(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        path,
        app_fs,
    ):
        """Check that field visible if advanced clicked."""

        config_page = create_cluster_and_open_config_page
        group_name = path.split("/")[-1]
        config_page.config.check_no_rows_or_groups_on_page()
        with config_page.config.wait_config_groups_change():
            config_page.config.click_on_advanced()
        config_page.config.check_group_is_active(group_name=group_name)
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=False,
            is_subs_visible=False,
        )
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=True,
            is_subs_visible=True,
        )

    @parametrize_by_data_subdirs(
        __file__,
        "group_advanced_true_invisible_false_field_advanced_true_invisible_true_activiatable_false",
    )
    def test_group_advanced_true_invisible_false_field_advanced_true_invisible_true_active_false(
        self,
        create_cluster_and_open_config_page,
        sdk_client_fs,
        path,
        app_fs,
    ):
        """Field always invisible."""

        config_page = create_cluster_and_open_config_page
        group_name = path.split("/")[-1]
        config_page.config.check_no_rows_or_groups_on_page()
        with config_page.config.wait_config_groups_change():
            config_page.config.click_on_advanced()
        config_page.config.check_group_is_active(group_name=group_name, is_active=False)
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=False,
            is_subs_visible=False,
        )
        config_page.check_groups(
            group_names=[group_name],
            is_group_visible=True,
            is_group_active=True,
            is_subs_visible=False,
        )
