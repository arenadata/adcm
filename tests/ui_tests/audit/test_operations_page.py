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
from typing import Callable, Collection

import allure
import pytest
import requests
from adcm_client.audit import AuditOperation, ObjectType, OperationResult, OperationType
from adcm_client.objects import (
    ADCMClient,
    Cluster,
    Component,
    Group,
    Host,
    Policy,
    Provider,
    Role,
    Service,
    User,
)
from tests.library.assertions import are_equal, tuples_are_equal
from tests.ui_tests.app.page.admin.page import OperationRowInfo, OperationsAuditPage
from tests.ui_tests.app.page.common.dialogs.operation_changes import ChangesRow
from tests.ui_tests.audit.utils import add_filter

# pylint: disable=redefined-outer-name

USER = {"username": "gegenaugh", "password": "awersomepass"}


@pytest.fixture()
def prepare_rbac_entries(sdk_client_fs) -> tuple[User, Group, Role, Policy]:
    user: User = sdk_client_fs.user_create(**USER, last_name="Bebe")
    group: Group = sdk_client_fs.group_create("Best Group Ever")
    group.add_user(user)
    user.update(email="not@ex.ist", last_name="Bobo")
    role = sdk_client_fs.role_create(
        name="somerole", display_name="Some role", child=[{"id": sdk_client_fs.role(name="View policy").id}]
    )
    policy: Policy = sdk_client_fs.policy_create(name="policy_name", role=role, user=[user])
    policy.update(description="Hoho Haha")
    role.update(description="Hehe Hihi")
    return user, group, role, policy


@pytest.fixture()
def prepare_cluster_objects(generic_cluster) -> tuple[Cluster, Service, Component]:
    service: Service = generic_cluster.service_add(name="simple_service")
    try:  # it's expected to fail
        service.config_set_diff({"key": False})
    # pylint: disable-next=bare-except
    except:  # noqa: E722
        pass
    service.component().config_set_diff({"key": "hehehe"})
    service.delete()
    service = generic_cluster.service_add(name="simple_service")
    return generic_cluster, service, service.component()


@pytest.fixture()
def prepare_provider_objects(sdk_client_fs, generic_provider) -> tuple[Provider, Host]:
    host = generic_provider.host_create("some-fqdn")
    host.config_set_diff({"key": "sfd"})
    generic_provider.config_set_diff({"key": "sfd"})
    user_client = ADCMClient(url=sdk_client_fs.url, user=USER["username"], password=USER["password"])
    # create denied record
    requests.delete(
        f"{user_client.url}/api/v1/host/{host.id}/", headers={"Authorization": f"Token {user_client.api_token()}"}
    )
    host.delete()
    return generic_provider, generic_provider.host_create("another-fqdn")


@pytest.fixture()
def prepare_audit_entries(sdk_client_fs, prepare_rbac_entries, prepare_cluster_objects, prepare_provider_objects):
    _ = prepare_rbac_entries, prepare_cluster_objects, prepare_provider_objects
    sdk_client_fs.adcm().config_set_diff({"ansible_settings": {"forks": 4}})
    return sdk_client_fs.audit_operation_list()


@pytest.mark.usefixtures("prepare_audit_entries", "_login_to_adcm_over_api")
def test_audit_operations_page(app_fs, sdk_client_fs):
    page = OperationsAuditPage(app_fs.driver, app_fs.adcm.url).open()

    _test_unfiltered_paging(client=sdk_client_fs, page=page)
    _test_filters_one_by_one(client=sdk_client_fs, page=page)
    _test_two_filters(client=sdk_client_fs, page=page)
    _test_object_changes(page=page)


@allure.step("Check unfiltered paging")
def _test_unfiltered_paging(client: ADCMClient, page: OperationsAuditPage):
    per_page = 10
    for i, page_num in enumerate(range(1, 4)):
        with allure.step(f"Check records on page #{page_num} ({per_page} per page)"):
            page.table.click_page_by_number(page_num)
            suitable_records = _get_filtered_audit_logs(
                client=client, start_from=i * per_page, finish_at=i * per_page + per_page
            )
            are_equal(page.table.row_count, len(suitable_records), "Unexpected amount of rows")
            expected_records = _convert_to_expected_audit_row_record(client=client, records=suitable_records)
            actual_records = page.get_info_from_all_rows()
            tuples_are_equal(actual_records, expected_records, "Unexpected records on page")

    per_page = 25
    with allure.step(f"Check setting {per_page} rows per page on 1st page"):
        page.table.click_page_by_number(1)
        page.table.set_rows_per_page(per_page)
        are_equal(page.table.row_count, per_page, "Incorrect amount of records per page")
        expected_records = _convert_to_expected_audit_row_record(
            client=client, records=_get_filtered_audit_logs(client=client, finish_at=per_page)
        )
        actual_records = page.get_info_from_all_rows()
        tuples_are_equal(actual_records, expected_records, "Unexpected records on page")

    with allure.step(f"Check second page when there's {per_page} records per page"):
        page.table.click_page_by_number(2)
        # it's expected there will be less than 50 records at this point
        suitable_records = _get_filtered_audit_logs(client=client, start_from=25, finish_at=50)
        are_equal(page.table.row_count, len(suitable_records), "Incorrect amount of records per page")
        expected_records = _convert_to_expected_audit_row_record(client=client, records=suitable_records)
        actual_records = page.get_info_from_all_rows()
        tuples_are_equal(actual_records, expected_records, "Unexpected records on page")

    page.table.set_rows_per_page(10)
    page.table.click_page_by_number(1)


def _test_filters_one_by_one(client: ADCMClient, page: OperationsAuditPage):
    _check_username_filter(client, page)
    _check_object_name_filter(client, page)
    _check_object_type_filter(client, page)
    _check_operation_type_filter(client, page)
    _check_operation_result_filter(client, page)


def _test_two_filters(client: ADCMClient, page: OperationsAuditPage):
    with allure.step("Add two filters and check records"):
        object_type_filter = add_filter(page=page, filter_menu_name="Object type")
        operation_type_filter = add_filter(page=page, filter_menu_name="Operation type")

        with page.table.wait_rows_change():
            page.pick_filter_value(filter_input=object_type_filter, value_to_pick="User")

        with page.table.wait_rows_change():
            page.pick_filter_value(filter_input=operation_type_filter, value_to_pick="Update")

        _check_records(
            client=client,
            page=page,
            filters=(
                lambda rec: rec.object_type == ObjectType.USER,
                lambda rec: rec.operation_type == OperationType.UPDATE,
            ),
        )

    with allure.step("Refresh one filter and only one filter is not applied"):
        with page.table.wait_rows_change():
            page.refresh_filter(1)

        _check_records(client=client, page=page, filters=(lambda rec: rec.object_type == ObjectType.USER,))

    with allure.step("Refresh page and cleanup filters"):
        page.driver.refresh()
        page.remove_filter(0)


@allure.step("Check object changes")
def _test_object_changes(page: OperationsAuditPage):
    object_type_filter = add_filter(page=page, filter_menu_name="Object type")
    operation_type_filter = add_filter(page=page, filter_menu_name="Operation type")

    page.pick_filter_value(filter_input=object_type_filter, value_to_pick="User")
    page.pick_filter_value(filter_input=operation_type_filter, value_to_pick="Update")

    are_equal(actual=page.table.row_count, expected=1, message="There should be exactly one record")

    changes_dialog = page.open_changes_dialog(page.table.get_row(0))

    changes = changes_dialog.get_changes()
    name_change = ChangesRow(attribute="Last name", old_value="Bebe", new_value="Bobo")
    email_change = ChangesRow(attribute="Email", old_value="", new_value="not@ex.ist")
    assert any(change == name_change for change in changes), f"Not found change: {name_change}\nFound: {changes}"
    assert any(change == email_change for change in changes), f"Not found change: {email_change}\nFound: {changes}"


@allure.step("Check 'Username' filter")
def _check_username_filter(client: ADCMClient, page: OperationsAuditPage):
    filter_input = add_filter(page=page, filter_menu_name="Username")

    with page.table.wait_rows_change():
        filter_input.send_keys(USER["username"])
        page.click_out_of_filter()

    user_id = client.user(username=USER["username"]).id
    _check_records(client=client, page=page, filters=(lambda rec: rec.user_id == user_id,))

    with page.table.wait_rows_change():
        page.remove_filter(filter_position=0)


@allure.step("Check 'Object name' filter")
def _check_object_name_filter(client: ADCMClient, page: OperationsAuditPage):
    provider_name = client.provider().name
    component: Component = client.component()
    component_full_name = f"{component.cluster().name}/{client.service(id=component.service_id).name}/{component.name}"
    filter_input = add_filter(page=page, filter_menu_name="Object name")

    for (value_to_type, filter_) in (
        (provider_name, lambda rec: rec.object_name == provider_name),
        (component_full_name, lambda rec: rec.object_name == component_full_name),
    ):
        filter_input.clear()
        filter_input.send_keys(value_to_type)
        page.click_out_of_filter()

        _check_records(client=client, page=page, filters=(filter_,))

    with page.table.wait_rows_change():
        page.remove_filter(filter_position=0)


@allure.step("Check 'Object type' filter")
def _check_object_type_filter(client: ADCMClient, page: OperationsAuditPage):
    filter_input = add_filter(page=page, filter_menu_name="Object type")

    for (value_to_pick, filter_) in (
        ("Host", lambda rec: rec.object_type == ObjectType.HOST),
        ("Policy", lambda rec: rec.object_type == ObjectType.POLICY),
    ):
        page.pick_filter_value(filter_input=filter_input, value_to_pick=value_to_pick)
        _check_records(client=client, page=page, filters=(filter_,))

    with page.table.wait_rows_change():
        page.remove_filter(filter_position=0)


@allure.step("Check 'Operation type' filter")
def _check_operation_type_filter(client: ADCMClient, page: OperationsAuditPage):
    filter_input = add_filter(page=page, filter_menu_name="Operation type")

    page.pick_filter_value(filter_input=filter_input, value_to_pick="Delete")
    _check_records(client=client, page=page, filters=(lambda rec: rec.operation_type == OperationType.DELETE,))

    page.pick_filter_value(filter_input=filter_input, value_to_pick="Update")
    suitable_records = _get_filtered_audit_logs(
        client=client, filters=(lambda rec: rec.operation_type == OperationType.UPDATE,)
    )
    are_equal(actual=page.table.row_count, expected=len(suitable_records), message="Incorrect amount of records")

    with page.table.wait_rows_change():
        page.table.set_rows_per_page(50)

    page.pick_filter_value(filter_input=filter_input, value_to_pick="Update")
    suitable_records = _get_filtered_audit_logs(
        client=client, finish_at=50, filters=(lambda rec: rec.operation_type == OperationType.UPDATE,)
    )
    are_equal(actual=page.table.row_count, expected=len(suitable_records), message="Incorrect amount of records")

    with page.table.wait_rows_change():
        page.remove_filter(filter_position=0)


@allure.step("Check 'Operation result' filter")
def _check_operation_result_filter(client: ADCMClient, page: OperationsAuditPage):
    filter_input = add_filter(page=page, filter_menu_name="Operation result")

    page.pick_filter_value(filter_input=filter_input, value_to_pick="Denied")
    _check_records(client=client, page=page, filters=(lambda rec: rec.operation_result == OperationResult.DENIED,))

    with page.table.wait_rows_change():
        page.remove_filter(filter_position=0)


def _check_records(client: ADCMClient, page: OperationsAuditPage, filters: list[Callable]) -> None:
    suitable_records = _get_filtered_audit_logs(client=client, filters=filters)
    are_equal(actual=page.table.row_count, expected=len(suitable_records), message="Incorrect amount of records")
    tuples_are_equal(
        actual=_convert_to_expected_audit_row_record(client=client, records=suitable_records),
        expected=page.get_info_from_all_rows(),
        message="Incorrect rows were filtered",
    )


def _convert_to_expected_audit_row_record(
    client: ADCMClient, records: tuple[AuditOperation, ...]
) -> tuple[OperationRowInfo, ...]:
    return tuple(
        OperationRowInfo(
            object_type=rec.object_type.value if rec.object_type else "",
            object_name=rec.object_name or "",
            operation_name=rec.operation_name,
            operation_type=rec.operation_type.value,
            operation_result=rec.operation_result.value,
            # e.g. Nov 8, 2022, 3:50:29 PM
            operation_time=rec.operation_time.astimezone(datetime.datetime.now().astimezone().tzinfo).strftime(
                "%b %-d, %Y, %-I:%M:%S %p"
            ),
            username=client.user(id=rec.user_id).username,
        )
        for rec in records
    )


def _get_filtered_audit_logs(
    client: ADCMClient,
    start_from: int = 0,
    finish_at: int = 10,
    filters: Collection[Callable[[AuditOperation], bool]] = (),
) -> tuple[AuditOperation]:
    logs_filter = filter(lambda _: True, client.audit_operation_list(paging={"offset": 0, "limit": 300}))

    for filter_func in filters:
        logs_filter = filter(filter_func, logs_filter)

    return tuple(list(logs_filter)[start_from:finish_at])
