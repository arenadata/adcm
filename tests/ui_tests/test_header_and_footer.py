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

"""UI tests for ADCM header and footer"""

import allure
import pytest

# from adcm_pytest_plugin.common import add_dummy_objects_to_adcm
from tests.ui_tests.app.page.admin.page import AdminIntroPage, AdminSettingsPage
from tests.ui_tests.app.page.bundle_list.page import BundleListPage
from tests.ui_tests.app.page.cluster_list.page import ClusterListPage
from tests.ui_tests.app.page.host_list.page import HostListPage
from tests.ui_tests.app.page.hostprovider_list.page import ProviderListPage
from tests.ui_tests.app.page.job_list.page import JobListPage
from tests.ui_tests.app.page.login.page import LoginPage
from tests.ui_tests.app.page.profile.page import ProfilePage
from tests.ui_tests.utils import close_current_tab, wait_for_new_window

pytestmark = [pytest.mark.usefixtures("_login_to_adcm_over_api")]


class TestHeader:
    """UI Tests for header"""

    def test_header_tabs_for_authorised_user(self, app_fs):
        """Test header buttons for authorised user"""
        intro_page = AdminIntroPage(app_fs.driver, app_fs.adcm.url)

        intro_page.header.click_arenadata_logo()
        intro_page.wait_url_contains_path(intro_page.path)

        intro_page.header.click_clusters_tab()
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url)
        cluster_page.wait_page_is_opened()

        cluster_page.header.click_hostproviders_tab()
        provider_page = ProviderListPage(app_fs.driver, app_fs.adcm.url)
        provider_page.wait_page_is_opened()

        provider_page.header.click_hosts_tab()
        host_page = HostListPage(app_fs.driver, app_fs.adcm.url)
        host_page.wait_page_is_opened()

        host_page.header.click_jobs_tab()
        job_page = JobListPage(app_fs.driver, app_fs.adcm.url)
        job_page.wait_page_is_opened()

        job_page.header.click_bundles_tab()
        bundle_page = BundleListPage(app_fs.driver, app_fs.adcm.url)
        bundle_page.wait_page_is_opened()

        bundle_page.header.click_job_block()
        job_page = JobListPage(app_fs.driver, app_fs.adcm.url)
        job_page.wait_page_is_opened()
        job_page.header.check_job_popup()

    def test_header_help_links_for_authorised_user(self, app_fs):
        """Test header help links for authorised user"""
        params = {
            "help_link": "t.me/arenadata_cm",
            "arenadata_url": "docs.arenadata.io/",
            "docs_link_en": "en/ADCM/current/introduction/",
        }
        page = AdminIntroPage(app_fs.driver, app_fs.adcm.url)
        header = page.header
        header.click_help_button()
        header.check_help_popup()
        with wait_for_new_window(app_fs.driver):
            header.click_ask_link_in_help_popup()
        with allure.step(f"Check new opened page: {params['help_link']}"):
            page.wait_url_contains_path(params["help_link"])
            close_current_tab(app_fs.driver)
        header.click_help_button()
        with wait_for_new_window(app_fs.driver):
            header.click_doc_link_in_help_popup()
        with allure.step(f"Check new opened page: {params['docs_link_en']}"):
            page.wait_url_contains_path(params["arenadata_url"] + params["docs_link_en"])

    def test_check_header_user_settings_for_authorised_user(self, app_fs):
        """Test header user settings buttons for authorised user"""
        page = AdminIntroPage(app_fs.driver, app_fs.adcm.url)
        page.header.click_account_button()
        page.header.check_account_popup()
        page.header.click_settings_link_in_acc_popup()
        page = AdminSettingsPage(app_fs.driver, app_fs.adcm.url)
        page.wait_page_is_opened()

        page.header.click_account_button()
        page.header.click_profile_link_in_acc_popup()
        page = ProfilePage(app_fs.driver, app_fs.adcm.url)
        page.wait_page_is_opened()

        page.header.click_account_button()
        page.header.click_logout_in_acc_popup()
        LoginPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()

    @pytest.mark.xfail(reason="https://arenadata.atlassian.net/browse/ADCM-2054")
    def test_check_back_button_in_browser_for_header_links(self, app_fs, sdk_client_fs):
        """Test browser back button after following header links"""
        with allure.step("Check back button for cluster page header link"):
            intro_page = AdminIntroPage(app_fs.driver, app_fs.adcm.url)
            intro_page.header.click_clusters_tab()
            cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url)
            cluster_page.wait_page_is_opened()
            cluster_page.click_back_button_in_browser()
            intro_page.wait_page_is_opened()

        with allure.step("Check back button for hostprovider page header link"):
            cluster_page.open()
            cluster_page.header.click_hostproviders_tab()
            hostprovider_page = ProviderListPage(app_fs.driver, app_fs.adcm.url)
            hostprovider_page.wait_page_is_opened()
            hostprovider_page.click_back_button_in_browser()
            cluster_page.wait_page_is_opened()

        with allure.step("Check back button for hosts page header link"):
            hostprovider_page.open()
            hostprovider_page.header.click_hosts_tab()
            hosts_page = HostListPage(app_fs.driver, app_fs.adcm.url)
            hosts_page.wait_page_is_opened()
            hosts_page.click_back_button_in_browser()
            hostprovider_page.wait_page_is_opened()

        with allure.step("Check back button for jobs page header link"):
            hosts_page.open()
            hosts_page.header.click_jobs_tab()
            jobs_page = JobListPage(app_fs.driver, app_fs.adcm.url)
            jobs_page.wait_page_is_opened()
            jobs_page.click_back_button_in_browser()
            hosts_page.wait_page_is_opened()

        with allure.step("Check back button for bundles page header link"):
            jobs_page.open()
            jobs_page.header.click_bundles_tab()
            bundles_page = BundleListPage(app_fs.driver, app_fs.adcm.url)
            bundles_page.wait_page_is_opened()
            bundles_page.click_back_button_in_browser()
            jobs_page.wait_page_is_opened()


class TestFooter:
    def test_check_footer_for_authorised_user(self, app_fs):
        """Test footer for authorised user"""
        params = {"arenadata_url": "docs.arenadata.io/", "docs": "en/ADCM/current/release-notes/"}
        page = AdminIntroPage(app_fs.driver, app_fs.adcm.url)
        footer = page.footer
        footer.check_all_elements()
        with wait_for_new_window(app_fs.driver):
            footer.click_version_link_in_footer()
        with allure.step(f"Check new opened page: {params['docs']}"):
            page.wait_url_contains_path(params["arenadata_url"] + params["docs"])
