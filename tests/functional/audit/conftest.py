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

"""conftest for audit tests"""

from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Literal, NamedTuple, Optional
from typing import OrderedDict as OrderedDictType
from typing import Union

import allure
import pytest
import requests
from adcm_client.audit import AuditLogin, AuditLoginList, AuditOperation, AuditOperationList
from adcm_client.base import ObjectNotFound
from adcm_client.objects import ADCMClient

from tests.functional.conftest import only_clean_adcm
from tests.functional.rbac.conftest import BusinessRoles
from tests.library.audit.checkers import AuditLogChecker
from tests.library.audit.readers import ParsedAuditLog, YAMLReader
from tests.library.db import Query, QueryExecutioner

# pylint: disable=redefined-outer-name

pytestmark = [only_clean_adcm]

AUDIT_LOG_SCENARIOS_DIR = Path(__file__).parent / "scenarios"

BUNDLES_DIR = Path(__file__).parent / "bundles"


class ScenarioArg(NamedTuple):
    """Wrapper for argument for audit log parser"""

    filename: str
    context: dict


@pytest.fixture(scope="session")
def audit_log_scenarios_reader() -> YAMLReader:
    """Create YAML reader aimed to scenarios dir"""
    return YAMLReader(AUDIT_LOG_SCENARIOS_DIR)


@pytest.fixture()
def parse_with_context(request, audit_log_scenarios_reader) -> Callable:
    """Returns the function prepared to parse file from request.param with given context"""
    return audit_log_scenarios_reader.prepare_parser_of(request.param)


@pytest.fixture()
def parsed_audit_log(request, audit_log_scenarios_reader) -> ParsedAuditLog:
    """Parse given file with given context"""
    if not request.param or not isinstance(request.param, ScenarioArg):
        raise ValueError(f"Param is required and it has to be {ScenarioArg.__class__.__name__}")
    return audit_log_scenarios_reader.parse(request.param.filename, request.param.context)


def parametrize_audit_scenario_parsing(scenario_name: str, context: Optional[dict] = None):
    """
    Helper to use as decorator to provide scenario name and context for parametrizing "parsed_audit_log"
    """
    context = {} if context is None else context
    return pytest.mark.parametrize("parsed_audit_log", [ScenarioArg(scenario_name, context)], indirect=True)


@pytest.fixture()
def audit_log_checker(parsed_audit_log) -> AuditLogChecker:
    """Create audit log checker based on parsed audit log"""
    return AuditLogChecker(parsed_audit_log)


# CREATE/DELETE utilities

NEW_USER = {
    "username": "newuser",
    "password": "fnwqoevj",
    "first_name": "young",
    "last_name": "manager",
    "email": "does@notexi.st",
}


class CreateDeleteOperation:
    """List of endpoints for convenience"""

    # UPLOAD (create only)
    LOAD = "stack/load"
    UPLOAD = "stack/upload"
    # BUNDLE (delete only)
    BUNDLE = "stack/bundle"
    # CREATE CLUSTER/PROVIDER objects
    CLUSTER = "cluster"
    PROVIDER = "provider"
    HOST = "host"
    HOST_FROM_PROVIDER = "provider/{provider_id}/host"
    # GROUP CONFIG
    GROUP_CONFIG = "group-config"
    # RBAC
    USER = "rbac/user"
    ROLE = "rbac/role"
    GROUP = "rbac/group"
    POLICY = "rbac/policy"


@pytest.fixture()
def rbac_create_data(sdk_client_fs) -> OrderedDictType[str, dict]:
    """Prepare data to create RBAC objects"""
    business_role = sdk_client_fs.role(name=BusinessRoles.ViewADCMSettings.value.role_name)
    adcm_user_role = sdk_client_fs.role(name="ADCM User")
    return OrderedDict(
        {
            "user": {**NEW_USER},
            "group": {"name": "groupforU"},
            "role": {
                "name": "newrole",
                "description": "Awesome role",
                "display_name": "New Role",
                "child": [{"id": business_role.id}],
            },
            "policy": {
                "name": "newpolicy",
                "description": "Best policy ever",
                "role": {"id": adcm_user_role.id},
                "user": [{"id": sdk_client_fs.me().id}],
                "group": [],
                "object": [],
            },
        }
    )


@pytest.fixture()
def prepare_settings(sdk_client_fs):
    """Prepare settings for correct log rotation / cleanup AND LDAP"""
    sdk_client_fs.adcm().config_set_diff(
        {
            "attr": {"logrotate": {"active": True}, "ldap_integration": {"active": True}},
            "config": {
                "job_log": {"log_rotation_on_fs": 10, "log_rotation_in_db": 10},
                "config_rotation": {"config_rotation_in_db": 1},
                "audit_data_retention": {"retention_period": 1},
                "ldap_integration": {
                    "ldap_uri": "ldap://doesnot.exist",
                    "ldap_user": "someuse",
                    "ldap_password": "password",
                    "user_search_base": "db=Users",
                    "group_search_base": "ldksjf",
                    "sync_interval": 1,
                },
            },
        }
    )


# requesting utilities


@pytest.fixture()
def post(sdk_client_fs) -> Callable:
    """
    Prepare POST caller with all required credentials, so you only need to give path.
    Body and stuff are optional.
    """
    base_url = sdk_client_fs.url
    auth_header = make_auth_header(sdk_client_fs)

    def _post(
        path: str,
        body: Optional[dict] = None,
        headers: Optional[dict] = None,
        path_fmt: Optional[dict] = None,
        **kwargs,
    ):
        body = {} if body is None else body
        headers = {**auth_header, **({} if headers is None else headers)}
        path_fmt = {} if path_fmt is None else path_fmt
        url = f"{base_url}/api/v1/{path.format(**path_fmt)}/"
        with allure.step(f"Sending POST request to {url} with body: {body}"):
            return requests.post(url, headers=headers, json=body, **kwargs)

    return _post


@pytest.fixture()
def delete(sdk_client_fs) -> Callable:
    """
    Prepare DELETE caller with all required credentials.
    Object ID can be passed via `suffixes`.
    """
    base_url = sdk_client_fs.url
    auth_header = make_auth_header(sdk_client_fs)

    def _delete(path: str, *suffixes, headers: Optional[dict] = None, path_fmt: Optional[dict] = None, **kwargs):
        headers = {**auth_header, **({} if headers is None else headers)}
        path_fmt = {} if path_fmt is None else path_fmt
        url = f'{base_url}/api/v1/{path.format(**path_fmt)}/{"/".join(map(str,suffixes))}/'
        with allure.step(f"Sending DELETE request to {url}"):
            return requests.delete(url, headers=headers, **kwargs)

    return _delete


@pytest.fixture()
def new_user_client(sdk_client_fs) -> ADCMClient:
    """Get or create new user"""
    try:
        user = sdk_client_fs.user(username=NEW_USER["username"])
    except ObjectNotFound:
        user = sdk_client_fs.user_create(**NEW_USER)
    return ADCMClient(url=sdk_client_fs.url, user=user.username, password=NEW_USER["password"])


@pytest.fixture()
def unauthorized_creds(new_user_client) -> Dict[Literal["Authorization"], str]:
    """Prepare authorization header for the new user (by default, no policies assigned)"""
    return make_auth_header(new_user_client)


@allure.step("Expecting request to succeed")
def check_succeed(response: requests.Response) -> requests.Response:
    """Check that request has succeeded"""
    allowed_codes = (200, 201, 204)
    assert (
        code := response.status_code
    ) in allowed_codes, (
        f"Request failed with code: {code}\nBody: {response.json() if not code >= 500 else response.text}"
    )
    return response


def check_failed(response: requests.Response, exact_code: Optional[int] = None) -> requests.Response:
    """Check that request has failed"""
    with allure.step(f'Expecting request to fail with code {exact_code if exact_code else ">=400 and < 500"}'):
        assert response.status_code < 500, "Request should not failed with 500"
        if exact_code:
            assert (
                response.status_code == exact_code
            ), f"Request was expected to be failed with {exact_code}, not {response.status_code}"
        else:
            assert response.status_code >= 400, (
                "Request was expected to be failed, "
                f"but status code was {response.status_code}.\nBody: {response.json()}"
            )
    return response


def check_400(response: requests.Response) -> requests.Response:
    """Check that request failed with 400 code"""
    return check_failed(response, 400)


def check_403(response: requests.Response) -> requests.Response:
    """Check that request failed with 403 code"""
    return check_failed(response, 403)


def check_404(response: requests.Response) -> requests.Response:
    """Check that request failed with 404 code"""
    return check_failed(response, 404)


def check_409(response: requests.Response) -> requests.Response:
    """Check that request failed with 409 code"""
    return check_failed(response, 409)


def make_auth_header(client: ADCMClient) -> dict:
    """Make authorization header based on API token from ADCM client"""
    return {"Authorization": f"Token {client.api_token()}"}


# !===== DB manipulations =====!


def format_date_for_db(date: datetime) -> str:
    """Format date to the SQLite datetime format"""
    return date.strftime("%Y-%m-%d %H:%M:%S.%f")


def set_operations_date(
    adcm_db: QueryExecutioner, new_date: datetime, operation_records: Union[AuditOperationList, List[AuditOperation]]
):
    """Set date for given operation audit records directly in ADCM database"""
    adcm_db.exec(
        Query("audit_auditlog")
        .update([("operation_time", format_date_for_db(new_date))])
        .where(id=tuple(map(lambda o: o.id, operation_records)))
    )


def set_logins_date(
    adcm_db: QueryExecutioner, new_date: datetime, login_records: Union[AuditLoginList, List[AuditLogin]]
):
    """Set date for given login audit records directly in ADCM database"""
    adcm_db.exec(
        Query("audit_auditsession")
        .update([("login_time", format_date_for_db(new_date))])
        .where(id=tuple(map(lambda o: o.id, login_records)))
    )
