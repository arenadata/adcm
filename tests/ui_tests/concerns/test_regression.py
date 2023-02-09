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
from pathlib import Path

import allure
import pytest
from adcm_client.objects import Cluster, Component, Service

from tests.library.assertions import tuples_are_equal
from tests.ui_tests.app.page.cluster.page import ClusterMainPage
from tests.ui_tests.app.page.cluster_list.page import ClusterListPage
from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.configuration.page import get_row_values
from tests.ui_tests.app.page.component.page import ComponentConfigPage
from tests.ui_tests.app.page.service.page import ServiceConfigPage

FIRST_SERVICE = (("ketchup", None), ("sandwich", [("cheese", "yesyesyes"), ("water", "nonono")]), ("plates", "12"))

SECOND_SERVICE = (
    ("pilaf", "delicious"),
    ("plates", "one but big"),
    ("components", [("rice", ""), ("water", ""), ("and_more", "")]),
)

LONELY_COMPONENT = (("Just Me", [("maybe_string", "")]), ("hey_there", "general"))

FIRST_COMPONENT = (("floor", "3"), ("wall", ""))

SECOND_COMPONENT = (("floor", "8"), ("wall", ""))


@pytest.fixture()
def cluster_objects(sdk_client_fs) -> tuple[Cluster, Service, Service]:
    bundle = sdk_client_fs.upload_from_fs(Path(__file__).parent / "bundles" / "couple_concerned_objects")
    cluster = bundle.cluster_create("Goose is not a Duck")
    return cluster, cluster.service_add(name="first_service"), cluster.service_add(name="second_service")


@allure.issue(url="https://tracker.yandex.ru/ADCM-3327")
@pytest.mark.usefixtures("_login_to_adcm_over_ui")
def test_config_renders_correctly_after_following_concern_links(  # pylint: disable=redefined-outer-name
    app_fs, cluster_objects
):
    cluster, first_service, second_service = cluster_objects
    current_page = ClusterListPage(driver=app_fs.driver, base_url=app_fs.adcm.url).open(close_popup=True)
    current_page.click_cluster_name_in_row(current_page.get_row_by_cluster_name(cluster.name))
    current_page = ClusterMainPage.from_page(current_page, cluster_id=cluster.id).wait_page_is_opened(timeout=2)

    current_page = follow_config_concern_link(current_page, cluster.name, first_service)
    check_displayed_config(current_page, FIRST_SERVICE)

    current_page = follow_config_concern_link(current_page, cluster.name, second_service)
    check_displayed_config(current_page, SECOND_SERVICE)

    current_page = follow_config_concern_link(
        current_page, second_service.display_name, second_service.component(name="lonely")
    )
    check_displayed_config(current_page, LONELY_COMPONENT)

    first_component = first_service.component(name="first_component")
    current_page = follow_config_concern_link(current_page, cluster.name, first_component)
    check_displayed_config(current_page, FIRST_COMPONENT)

    second_component = first_service.component(name="second_component")
    current_page = follow_config_concern_link(current_page, first_service.display_name, second_component)
    check_displayed_config(current_page, SECOND_COMPONENT)


@allure.step("Check config is displayed correctly")
def check_displayed_config(page, expected: tuple) -> None:
    displayed_config = tuple(get_row_values(page.config.get_rows(), convert_child=tuple))
    tuples_are_equal(actual=displayed_config, expected=expected)


def follow_config_concern_link(
    page: BasePageObject, breadcrumb_name: str, object_with_concern: Service | Component
) -> ServiceConfigPage | ComponentConfigPage:
    with allure.step(f"Follow concern link of '{object_with_concern.display_name}' from '{breadcrumb_name}' '!' mark"):
        popover = page.header.get_breadcrumbs().crumbs.named(breadcrumb_name.upper()).get_concern_mark().hover()
        popover.concerns.with_link(object_with_concern.display_name).first.click()

        if isinstance(object_with_concern, Service):
            config_page = ServiceConfigPage.from_page(
                page, cluster_id=object_with_concern.cluster_id, service_id=object_with_concern.id
            )
        elif isinstance(object_with_concern, Component):
            config_page = ComponentConfigPage.from_page(
                page,
                cluster_id=object_with_concern.cluster_id,
                service_id=object_with_concern.service_id,
                component_id=object_with_concern.id,
            )
        else:
            raise ValueError(f"Incorrect type of {object_with_concern}")

        config_page.wait_page_is_opened(timeout=2)
        config_page.check_all_elements()
        return config_page
