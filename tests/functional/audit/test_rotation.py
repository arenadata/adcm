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

"""Test audit logs rotation"""

import csv
import io
import json
import tarfile
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Collection, Dict, List, OrderedDict, Set, Union

import allure
import pytest
from adcm_client.audit import AuditLogin, AuditOperation, ObjectType, OperationType
from adcm_client.objects import ADCMClient
from adcm_client.wrappers.api import ADCMApiError
from adcm_pytest_plugin.docker.adcm import ADCM
from adcm_pytest_plugin.docker.commands import clearaudit
from adcm_pytest_plugin.docker.utils import get_file_from_container
from adcm_pytest_plugin.utils import random_string

from tests.functional.audit.conftest import (
    BUNDLES_DIR,
    set_logins_date,
    set_operations_date,
)
from tests.library.assertions import sets_are_equal
from tests.library.db import QueryExecutioner

# pylint: disable=redefined-outer-name


DATA_DIR = "/adcm/data"
AUDIT_DIR = f"{DATA_DIR}/audit/"
ARCHIVE_NAME = "audit_archive.tar.gz"

DOOMED_CLUSTER_NAME = "Doomed Cluster"

# !===== Fixtures =====!


@pytest.fixture()
def logins_to_be_archived(
    sdk_client_fs: ADCMClient, adcm_db: QueryExecutioner, adcm_api_credentials: dict
) -> List[AuditLogin]:
    """
    Create new user and make login attempts.

    :returns: List of login audit records which dates were changed to the old ones.
    """
    admin_credentials = {
        "username": adcm_api_credentials["user"],
        "password": adcm_api_credentials["password"],
    }
    user_creds = {"username": "user1", "password": "password1password1"}
    not_existing_user = {"username": "user2", "password": "password1password1"}
    existing_logs: Set[int] = {rec.id for rec in sdk_client_fs.audit_login_list()}
    with allure.step("Create one more user and try to login with different pairs"):
        sdk_client_fs.user_create(**user_creds)
        for _ in range(2):
            for creds in (
                admin_credentials,
                user_creds,
                not_existing_user,
                {**user_creds, "password": "wrongpass"},
            ):
                try:
                    ADCMClient(url=sdk_client_fs.url, user=creds["username"], password=creds["password"])
                except ADCMApiError:
                    # failed logins should be ignored
                    pass
    new_date = datetime.utcnow() - timedelta(days=300)
    with allure.step(f"Change date of operations on already deleted cluster to {new_date}"):
        new_logs = list(filter(lambda rec: rec.id not in existing_logs, sdk_client_fs.audit_login_list()))
        old_logs = new_logs[: len(new_logs) // 2]
        set_logins_date(adcm_db, new_date, old_logs)
        assert len(old_logs) != 0, "There should be at least 1 login audit record"
    _ = [rec.reread() for rec in old_logs]
    return old_logs


@pytest.fixture()
def operation_to_be_archived(sdk_client_fs: ADCMClient, adcm_db: QueryExecutioner) -> List[AuditOperation]:
    """
    Create two clusters, work with them, then delete one.
    Then create-delete another one to create "deleted" audit object with existing audit records.

    :returns: List of operations which dates were changed to the old ones.
    """
    with allure.step("Create two clusters and perform some actions with them"):
        provider = sdk_client_fs.provider()
        hosts = [provider.host_create(f"host-{i}") for i in range(4)]
        bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / "adb")
        doomed_cluster = bundle.cluster_create(DOOMED_CLUSTER_NAME)
        create_operation = sdk_client_fs.audit_operation(
            operation_type=OperationType.CREATE, object_name=doomed_cluster.name
        )
        lucky_cluster = bundle.cluster_create("Lucky Cluster")
        for cluster in (doomed_cluster, lucky_cluster):
            cluster.config_set_diff({"just_string": random_string(12)})
            component = cluster.service_add(name="adb").component()
            host_1 = cluster.host_add(hosts.pop())
            cluster.host_add(hosts.pop())
            cluster.hostcomponent_set((host_1, component))
        service = doomed_cluster.service_add(name="dummy")
        doomed_cluster.service_delete(service)
        doomed_cluster.delete()
    new_date = datetime.utcnow() - timedelta(days=300)
    bundle.cluster_create("temp cluster").delete()
    with allure.step(f"Change date of operations on already deleted cluster to {new_date}"):
        doomed_cluster_operations: List[AuditOperation] = [
            operation
            for operation in sdk_client_fs.audit_operation_list(object_type=ObjectType.CLUSTER)
            if operation.object_id == create_operation.object_id
        ] + list(sdk_client_fs.audit_operation_list(object_type=ObjectType.BUNDLE))
        set_operations_date(adcm_db, new_date, doomed_cluster_operations)
        assert len(doomed_cluster_operations) != 0, "There should be at least 1 operation record"
    _ = [rec.reread() for rec in doomed_cluster_operations]
    return doomed_cluster_operations


# !===== Tests =====!


@pytest.mark.usefixtures("generic_provider")
def test_cleanup_with_archiving(adcm_fs, sdk_client_fs, logins_to_be_archived, operation_to_be_archived):
    """
    Test that audit logs are correctly archived
    """
    with allure.step("Configure ADCM to clean logs after 100 days"):
        sdk_client_fs.adcm().config_set_diff(
            {"audit_data_retention": {"retention_period": 100, "data_archiving": True}}
        )
    clearaudit(adcm_fs)
    archives = get_parsed_archive_files(adcm_fs)
    operations_expected_in_archive = tuple(map(AuditRecordConverter.to_archive_record, operation_to_be_archived))
    logins_expected_in_archive = tuple(map(AuditRecordConverter.to_archive_record, logins_to_be_archived))
    today = datetime.utcnow().date().strftime("%Y-%m-%d")
    operations_filename = f"audit_{today}_operations.csv"
    logins_filename = f"audit_{today}_logins.csv"
    objects_filename = f"audit_{today}_objects.csv"
    _check_all_archives_are_presented(archives.keys())
    with allure.step("Check operations records in archive are correct"):
        operations_records = archives[operations_filename]
        _check_records_are_correct(
            operations_records,
            operations_expected_in_archive,
            AuditRecordConverter.get_audit_operations_archive_headers(),
        )
    with allure.step("Check login records in archive are correct"):
        _check_records_are_correct(
            archives[logins_filename],
            logins_expected_in_archive,
            AuditRecordConverter.get_audit_logins_archive_headers(),
            exclude_from_comparison=(),
        )
    _check_audit_objects_records(archives[objects_filename])
    _check_old_audit_logs_are_removed(sdk_client_fs, operation_to_be_archived, logins_to_be_archived)


@pytest.mark.usefixtures("generic_provider")
def test_just_cleanup_audit_logs(adcm_fs, sdk_client_fs, logins_to_be_archived, operation_to_be_archived):
    """
    Test that running cleanup without allowing data archiving doesn't lead to creating archive
    and the same is when nothing to archive
    """
    with allure.step("Configure ADCM to clean logs after 100 days"):
        sdk_client_fs.adcm().config_set_diff(
            {"audit_data_retention": {"retention_period": 100, "data_archiving": False}}
        )
    operations_to_be_deleted = {o.id for o in operation_to_be_archived}
    operations_should_stay = {
        o.id for o in sdk_client_fs.audit_operation_list(paging={"limit": 200}) if o.id not in operations_to_be_deleted
    }
    clearaudit(adcm_fs)
    _check_old_audit_logs_are_removed(sdk_client_fs, operation_to_be_archived, logins_to_be_archived)
    with allure.step("Check that wrong operations were not deleted"):
        operations_left = {o.id for o in sdk_client_fs.audit_operation_list(paging={"limit": 200})}
        assert all(
            operation_id in operations_left for operation_id in operations_should_stay
        ), "More audit operation records were deleted that expected"
    _check_archive_dir_does_not_exist(adcm_fs)
    clearaudit(adcm_fs)
    with allure.step("Configure ADCM to archive audit logs"):
        sdk_client_fs.adcm().config_set_diff(
            {"audit_data_retention": {"retention_period": 100, "data_archiving": True}}
        )
    _check_archive_dir_does_not_exist(adcm_fs)  # because nothing to store


# !===== Steps =====!


def _check_all_archives_are_presented(
    archive_names: Collection[str], suffixes: Collection[str] = ("operations", "logins", "objects")
) -> None:
    today = datetime.utcnow().date().strftime("%Y-%m-%d")
    for suffix in suffixes:
        expected_filename = f"audit_{today}_{suffix}.csv"
        with allure.step(f"Check file {expected_filename} is in audit archive"):
            assert expected_filename in archive_names, "Archive file was not found"


def _check_records_are_correct(
    archive_records: List[Dict[str, Any]],
    expected_records: List[Dict[str, Any]],
    expected_headers: Set[str],
    exclude_from_comparison: Collection[str] = ("audit_object_id",),
) -> None:
    """Actual records shouldn't be empty"""
    with allure.step("Check headers"):
        # headers are based on first line of the archive, so they'll be the same for each record
        actual_headers = set(archive_records[0].keys())
        sets_are_equal(actual_headers, expected_headers, f"Incorrect headers in archive: {actual_headers}")
    with allure.step("Check all expected records are presented"):
        assert (actual := len(archive_records)) == (
            expected := len(expected_records)
        ), f"Incorrect amount of records.\nExpected: {expected}.\nFound: {actual}"
        cleaned_archive_records = [
            {k: v for k, v in rec.items() if k not in exclude_from_comparison} for rec in archive_records
        ]
        for expected in expected_records:
            if not any(actual_record == expected for actual_record in cleaned_archive_records):
                allure.attach(
                    json.dumps(archive_records, indent=2),
                    f'Records from archive (not compared fields: {", ".join(exclude_from_comparison)})',
                    attachment_type=allure.attachment_type.JSON,
                )
                raise AssertionError(f"None of records matched {expected}")


@allure.step("Check old audit logs are removed")
def _check_old_audit_logs_are_removed(
    client: ADCMClient, old_operations: List[AuditOperation], old_logins: List[AuditLogin]
):
    def get_ids(recs):
        return set(rec.id for rec in recs)

    existing_operation_logs = get_ids(client.audit_operation_list())
    deleted_operation_logs = get_ids(old_operations)
    found_operations = existing_operation_logs & deleted_operation_logs
    if found_operations:
        raise AssertionError(f"Some operation audit logs were not deleted: {found_operations}")

    existing_login_logs = get_ids(client.audit_login_list())
    deleted_login_logs = get_ids(old_logins)
    found_operations = existing_login_logs & deleted_login_logs
    if found_operations:
        raise AssertionError(f"Some login audit logs were not deleted: {found_operations}")


@allure.step('Check that only "deleted" audit object without records is in objects file')
def _check_audit_objects_records(records: List[Dict[str, Any]]):
    assert len(records) == 1, "There should be only 1 audit object in archive with deleted audit objects"
    object_record = records[0]
    assert (
        actual := set(object_record.keys())
    ) == AuditRecordConverter.get_audit_objects_archive_headers(), (
        f'Incorrect headers in audit objects archive file: {", ".join(actual)}'
    )
    assert (
        actual := object_record["object_type"]
    ) == ObjectType.CLUSTER.value, f"Object type should be cluster, not {actual}"
    assert (
        actual := object_record["object_name"]
    ) == DOOMED_CLUSTER_NAME, (
        f"Incorrect object name in audit objects archive: {actual}.\nExpected: {DOOMED_CLUSTER_NAME}"
    )


@allure.step("Check archive directory was not created")
def _check_archive_dir_does_not_exist(adcm: ADCM):
    files_in_data_dir = adcm.container.exec_run(["ls", DATA_DIR]).output.decode("utf-8").split()
    assert AUDIT_DIR not in files_in_data_dir, "Directory with archive file should not exist"


# !===== Utilities =====!


class AuditRecordConverter:
    """Converter of audit records (operation/login) to different formats"""

    _FIELDS = {
        AuditOperation: (
            "id",
            "operation_name",
            "operation_type",
            "operation_result",
            "operation_time",
            "object_changes",
            "user_id",
        ),
        AuditLogin: ("id", "login_result", "login_time", "login_details", "user_id"),
    }

    @classmethod
    def get_audit_operations_archive_headers(cls) -> Set[str]:
        """Get headers that should be presented in operations audit archive"""
        return set(cls._FIELDS[AuditOperation]) | {"audit_object_id"}

    @classmethod
    def get_audit_logins_archive_headers(cls) -> Set[str]:
        """Get headers that should be presented in login audit archive"""
        return set(cls._FIELDS[AuditLogin])

    @classmethod
    def get_audit_objects_archive_headers(cls) -> Set[str]:
        """Get headers that should be presented in audit objects archive"""
        return {"id", "object_id", "object_name", "object_type", "is_deleted"}

    @classmethod
    def to_archive_record(cls, record: Union[AuditOperation, AuditLogin]) -> dict:
        """Convert record to a dictionary in format how it should be extracted from audit records archive"""
        fields = cls._FIELDS.get(record.__class__, None)
        if fields is None:
            raise TypeError(f"`record` should be an instance of either {AuditOperation} or {AuditLogin}")
        return {field: str(cls._convert(getattr(record, field))) for field in fields}

    @classmethod
    def to_cef_record(cls, record: Union[AuditOperation, AuditLogin]) -> str:
        """Convert record to a log string in CEF format"""
        raise NotImplementedError

    @staticmethod
    def _convert(val):
        if isinstance(val, Enum):
            return val.value
        if isinstance(val, datetime):
            date = val.strftime("%Y-%m-%d %H:%M:%S.%f%z")
            # all of this to add ":" to timezone
            if date[-5] in ("+", "-"):
                date = f"{date[:-2]}:{date[-2:]}"
            return date
        if isinstance(val, OrderedDict):
            # for correct cast to string
            return dict(val)
        return val


def get_parsed_archive_files(adcm: ADCM) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get audit archive files from ADCM and return them in dict format,
    where keys are names of files from archive and values are lists with dicts (parsed csv file values)
    """

    with allure.step(f"Get archive {ARCHIVE_NAME} from ADCM container and parse CSV files"):
        archive = get_file_from_container(adcm, AUDIT_DIR, ARCHIVE_NAME).read()
        file_obj = io.BytesIO()
        file_obj.write(archive)
        file_obj.seek(0)
        records_in_files = {}
        with tarfile.open(mode="r", fileobj=file_obj) as tar:
            for member in tar.getmembers():
                lines = [line.decode("utf-8") for line in tar.extractfile(member.name).readlines()]
                records_in_files[member.name] = list(csv.DictReader(lines[1:], fieldnames=lines[0].strip().split(",")))
        return records_in_files
