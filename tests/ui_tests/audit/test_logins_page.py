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

import datetime
from collections.abc import Callable, Collection
from zoneinfo import ZoneInfo

import allure
import pytest
import requests
from adcm_client.audit import AuditLogin, LoginResult
from adcm_client.objects import ADCMClient

from tests.library.assertions import are_equal, tuples_are_equal
from tests.ui_tests.app.page.admin.page import LoginAuditPage, LoginRowInfo
from tests.ui_tests.audit.utils import add_filter

USER = {"username": "user", "password": "user"}


@pytest.fixture()
def user_credentials(sdk_client_fs: ADCMClient) -> tuple[str, str]:
    username = USER["username"]
    password = USER["password"]
    sdk_client_fs.user_create(username=username, password=password)
    return username, password


@pytest.fixture()
def inactive_user_credentials(sdk_client_fs: ADCMClient) -> tuple[str, str]:
    username = password = "incative"
    sdk_client_fs.user_create(username=username, password=password, is_active=False)
    return username, password


@pytest.fixture()
def _prepare_records(
    sdk_client_fs: ADCMClient,
    user_credentials: tuple[str, str],  # pylint: disable=redefined-outer-name
    inactive_user_credentials: tuple[str, str],  # pylint: disable=redefined-outer-name
) -> None:
    auth_url = f"{sdk_client_fs.url}/api/v1/token/"
    new_username, new_password = user_credentials
    inactive_username, inactive_password = inactive_user_credentials
    for _ in range(4):
        requests.post(auth_url, json={"username": "admin", "password": "wrongpass"})
        requests.post(auth_url, json={"username": "admin", "password": "admin"})
        requests.post(auth_url, json={"username": new_username, "password": "wrongpass"})
        requests.post(auth_url, json={"username": new_username, "password": new_password})
        requests.post(auth_url, json={"username": inactive_username, "password": "wrongpass"})
        requests.post(auth_url, json={"username": inactive_password, "password": new_password})
        requests.post(auth_url, json={"username": "wheres", "password": "theparty"})


@pytest.mark.usefixtures("_prepare_records", "_login_to_adcm_over_api")
def test_audit_login_page(app_fs, sdk_client_fs):
    page = LoginAuditPage(base_url=sdk_client_fs.url, driver=app_fs.driver).open()
    _test_unfiltered_paging(client=sdk_client_fs, page=page)
    _test_filters_one_by_one(client=sdk_client_fs, page=page)
    _test_two_filters(client=sdk_client_fs, page=page)


def _test_unfiltered_paging(client: ADCMClient, page: LoginAuditPage):
    per_page = 10

    for i, page_num in enumerate(range(1, 4)):
        with allure.step(f"Check records on page #{page_num} ({per_page} per page)"):
            page.table.click_page_by_number(page_num)
            are_equal(page.table.row_count, per_page, "Unexpected amount of rows")
            suitable_records = _get_filtered_audit_logs(
                client=client,
                start_from=i * per_page,
                finish_at=i * per_page + per_page,
            )
            expected_records = _convert_to_expected_audit_row_record(records=suitable_records)
            actual_records = page.get_info_from_all_rows()
            tuples_are_equal(actual_records, expected_records, "Unexpected records on page")

    per_page = 25
    with allure.step(f"Check setting {per_page} rows per page on 1st page"):
        page.table.click_page_by_number(1)
        page.table.set_rows_per_page(per_page)
        are_equal(page.table.row_count, per_page, "Incorrect amount of records per page")
        expected_records = _convert_to_expected_audit_row_record(
            records=_get_filtered_audit_logs(client=client, finish_at=per_page),
        )
        actual_records = page.get_info_from_all_rows()
        tuples_are_equal(actual_records, expected_records, "Unexpected records on page")

    with allure.step(f"Check second page when there's {per_page} records per page"):
        page.table.click_page_by_number(2)
        # it's expected there will be less than 50 records at this point
        suitable_records = _get_filtered_audit_logs(client=client, start_from=25, finish_at=50)
        are_equal(page.table.row_count, len(suitable_records), "Incorrect amount of records per page")
        expected_records = _convert_to_expected_audit_row_record(records=suitable_records)
        actual_records = page.get_info_from_all_rows()
        tuples_are_equal(actual_records, expected_records, "Unexpected records on page")

    page.table.set_rows_per_page(10)
    page.table.click_page_by_number(1)


def _test_filters_one_by_one(client: ADCMClient, page: LoginAuditPage):
    _check_login_filter(client, page)
    _check_result_filter(client, page)


def _test_two_filters(client: ADCMClient, page: LoginAuditPage):
    with allure.step("Add two filters and check records"):
        login_filter = add_filter(page=page, filter_menu_name="Login")
        result_filter = add_filter(page=page, filter_menu_name="Result")

        with page.table.wait_rows_change():
            login_filter.send_keys("user")
            page.click_out_of_filter()

        with page.table.wait_rows_change():
            page.pick_filter_value(filter_input=result_filter, value_to_pick="Wrong password")

        _check_records(
            client=client,
            page=page,
            filters=(
                lambda rec: rec.login_details and rec.login_details.get("username") == "user",
                lambda rec: rec.login_result == LoginResult.WRONG_PASSWORD,
            ),
        )

    with allure.step("Refresh one filter and only one filter is not applied"):
        with page.table.wait_rows_change():
            page.refresh_filter(1)

        _check_records(
            client=client,
            page=page,
            filters=(lambda rec: rec.login_details and rec.login_details.get("username") == "user",),
        )


@allure.step("Check 'Login' filter")
def _check_login_filter(client: ADCMClient, page: LoginAuditPage):
    filter_input = add_filter(page=page, filter_menu_name="Login")

    with page.table.wait_rows_change():
        filter_input.send_keys(USER["username"])
        page.click_out_of_filter()

    user_id = client.user(username=USER["username"]).id
    _check_records(client=client, page=page, filters=(lambda rec: rec.user_id == user_id,))

    with page.table.wait_rows_change():
        page.remove_filter(filter_position=0)


@allure.step("Check 'Login result' filter")
def _check_result_filter(client: ADCMClient, page: LoginAuditPage):
    filter_input = add_filter(page=page, filter_menu_name="Result")

    page.pick_filter_value(filter_input=filter_input, value_to_pick="Account disabled")
    _check_records(client=client, page=page, filters=(lambda rec: rec.login_result == LoginResult.DISABLED,))

    with page.table.wait_rows_change():
        page.remove_filter(filter_position=0)


def _check_records(client: ADCMClient, page: LoginAuditPage, filters: list[Callable]) -> None:
    suitable_records = _get_filtered_audit_logs(client=client, filters=filters)
    are_equal(actual=page.table.row_count, expected=len(suitable_records), message="Incorrect amount of records")
    tuples_are_equal(
        actual=_convert_to_expected_audit_row_record(records=suitable_records),
        expected=page.get_info_from_all_rows(),
        message="Incorrect rows were filtered",
    )


def _convert_to_expected_audit_row_record(records: tuple[AuditLogin, ...]) -> tuple[LoginRowInfo, ...]:
    return tuple(
        LoginRowInfo(
            login=rec.login_details["username"] if rec.login_details and "username" in rec.login_details else "",
            result=rec.login_result.value,
            # e.g. Nov 8, 2022, 3:50:29 PM
            login_time=rec.login_time.astimezone(
                datetime.datetime.now(tz=ZoneInfo("UTC")).astimezone().tzinfo,
            ).strftime(
                "%b %-d, %Y, %-I:%M:%S %p",
            ),
        )
        for rec in records
    )


def _get_filtered_audit_logs(
    client: ADCMClient,
    start_from: int = 0,
    finish_at: int = 10,
    filters: Collection[Callable[[AuditLogin], bool]] = (),
) -> tuple[AuditLogin]:
    logs_filter = filter(lambda _: True, client.audit_login_list(paging={"offset": 0, "limit": 300}))

    for filter_func in filters:
        logs_filter = filter(filter_func, logs_filter)

    return tuple(list(logs_filter)[start_from:finish_at])
