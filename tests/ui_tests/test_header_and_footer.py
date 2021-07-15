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
# pylint: disable=W0621

import allure

from tests.ui_tests.app.page.admin_intro.admin_intro_page import AdminIntroPage
from tests.ui_tests.app.page.admin_setttings_page.admin_settings import AdminSettingsPage
from tests.ui_tests.app.page.bundle_list_page.bundle_list import BundleListPage
from tests.ui_tests.app.page.cluster_list_page.cluster_list import ClusterListPage
from tests.ui_tests.app.page.common.base_page import (
    PageHeader,
    PageFooter,
)
from tests.ui_tests.app.page.host_list_page.host_list import HostListPage
from tests.ui_tests.app.page.hostprovider_list_page.hostprovider_list import ProviderListPage
from tests.ui_tests.app.page.job_list_page.job_list import JobListPage
from tests.ui_tests.app.page.login.login_page import LoginPage
from tests.ui_tests.app.page.profile_page.profile import ProfilePage
from tests.ui_tests.utils import (
    wait_for_new_window,
    close_current_tab,
)


def test_check_header_tabs_for_authorised_user(app_fs, login_to_adcm):
    header = PageHeader(app_fs.driver, app_fs.adcm.url)

    header.click_arenadata_logo_in_header()
    intro_page = AdminIntroPage(app_fs.driver, app_fs.adcm.url)
    header.wait_url_contains_path(intro_page.path)

    header.click_cluster_tab_in_header()
    cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url)
    header.wait_url_contains_path(cluster_page.path)

    header.click_hostproviders_tab_in_header()
    provider_page = ProviderListPage(app_fs.driver, app_fs.adcm.url)
    header.wait_url_contains_path(provider_page.path)

    header.click_hosts_tab_in_header()
    host_page = HostListPage(app_fs.driver, app_fs.adcm.url)
    header.wait_url_contains_path(host_page.path)

    header.click_jobs_tab_in_header()
    job_page = JobListPage(app_fs.driver, app_fs.adcm.url)
    header.wait_url_contains_path(job_page.path)

    header.click_bundles_tab_in_header()
    bundle_page = BundleListPage(app_fs.driver, app_fs.adcm.url)
    header.wait_url_contains_path(bundle_page.path)

    header.click_job_block_in_header()
    job_page = JobListPage(app_fs.driver, app_fs.adcm.url)
    header.wait_url_contains_path(job_page.path)
    header.check_job_popup()


def test_check_header_help_links_for_authorised_user(app_fs, login_to_adcm):
    params = {
        "help_link": "t.me/joinchat/",
        "docs_link": "docs.arenadata.io/adcm/"
    }
    header = PageHeader(app_fs.driver, app_fs.adcm.url)
    header.click_help_button_in_header()
    header.check_help_popup()
    with wait_for_new_window(app_fs.driver):
        header.click_ask_link_in_help_popup()
    with allure.step("Check new opened page"):
        assert params["help_link"] in app_fs.driver.current_url, \
            f"Page {params['help_link']} has not been opened"
        close_current_tab(app_fs.driver)
    header.click_help_button_in_header()
    with wait_for_new_window(app_fs.driver):
        header.click_doc_link_in_help_popup()
    with allure.step("Check new opened page"):
        assert params["docs_link"] in app_fs.driver.current_url, \
            f"Page {params['docs_link']} has not been opened"


def test_check_header_user_settings_for_authorised_user(app_fs, login_to_adcm):
    header = PageHeader(app_fs.driver, app_fs.adcm.url)
    header.click_account_button_in_header()
    header.check_account_popup()
    header.click_settings_link_in_acc_popup()
    header.wait_url_contains_path(AdminSettingsPage(app_fs.driver, app_fs.adcm.url).path)

    header.click_account_button_in_header()
    header.click_profile_link_in_acc_popup()
    header.wait_url_contains_path(ProfilePage(app_fs.driver, app_fs.adcm.url).path)

    header.click_account_button_in_header()
    header.click_logout_in_acc_popup()
    header.wait_url_contains_path(LoginPage(app_fs.driver, app_fs.adcm.url).path)


def test_check_footer_for_authorised_user(app_fs, login_to_adcm):
    params = {"docs": "docs.arenadata.io/adcm/notes"}
    footer = PageFooter(app_fs.driver, app_fs.adcm.url)
    footer.check_all_elements()
    with wait_for_new_window(app_fs.driver):
        footer.click_version_link_in_footer()
    with allure.step("Check new opened page"):
        assert params["docs"] in app_fs.driver.current_url, \
            f"Page {params['docs']} has not been opened"
