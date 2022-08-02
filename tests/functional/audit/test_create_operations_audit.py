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

"""
Test audit operations with "operation_type == CREATE"
"""

from pathlib import Path
from typing import Optional, Callable

import allure
import pytest
import requests

from tests.functional.audit.conftest import BUNDLES_DIR, ScenarioArg

# pylint: disable=redefined-outer-name


class CreateOperation:
    """List of endpoints for convenience"""

    # UPLOAD
    LOAD = 'stack/load'
    UPLOAD = 'stack/upload'
    # CREATE CLUSTER/PROVIDER objects
    CLUSTER = 'cluster'
    PROVIDER = 'provider'
    HOST = 'host'
    HOST_FROM_PROVIDER = 'provider/{provider_id}/host'
    # GROUP CONFIG
    GROUP_CONFIG = 'group-config'
    # RBAC
    USER = 'rbac/user'
    ROLE = 'rbac/role'
    GROUP = 'rbac/group'
    POLICY = 'rbac/policy'
    TOKEN = 'rbac/token'  # ?


@pytest.fixture()
def post(sdk_client_fs) -> Callable:
    """
    Prepare POST caller with all required credentials, so you only need to give path.
    Body and stuff are optional.
    """
    base_url = sdk_client_fs.url
    auth_header = {'Authorization': f'Token {sdk_client_fs.api_token()}'}

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
        return requests.post(f'{base_url}/api/v1/{path.format(**path_fmt)}/', headers=headers, json=body, **kwargs)

    return _post


@pytest.mark.parametrize(
    'bundle_archives',
    [
        [
            str(BUNDLES_DIR / 'create' / bundle_dir)
            for bundle_dir in ('incorrect_cluster', 'incorrect_provider', 'cluster', 'provider')
        ]
    ],
    indirect=True,
)
@pytest.mark.parametrize('parsed_audit_log', [ScenarioArg('create_load_upload.yaml', {})], indirect=True)
def test_bundle_upload_load(audit_log_checker, post, bundle_archives, sdk_client_fs):
    """Test audit logs for CREATE operations: stack/upload and stack/load"""
    incorrect_cluster_bundle, incorrect_provider_bundle, cluster_bundle, provider_bundle = tuple(
        map(Path, bundle_archives)
    )
    with allure.step('Upload and load incorrect bundles'):
        for bundle_path in (incorrect_cluster_bundle, incorrect_provider_bundle):
            with bundle_path.open('rb') as f:
                _check_succeed(post(CreateOperation.UPLOAD, files={'file': f}))
            _check_failed(post(CreateOperation.LOAD, {'bundle_file': bundle_path.name}))
    with allure.step('Upload and load correct bundles'):
        for bundle_path in (cluster_bundle, provider_bundle):
            with bundle_path.open('rb') as f:
                _check_succeed(post(CreateOperation.UPLOAD, files={'file': f}))
            _check_succeed(post(CreateOperation.LOAD, {'bundle_file': bundle_path.name}))
    with allure.step('Load/Upload with incorrect data in request'):
        _check_failed(post(CreateOperation.UPLOAD, files={'wrongkey': 'sldkj'}))
        _check_failed(post(CreateOperation.LOAD, {'bundle': 'somwthign'}))
    audit_log_checker.check(sdk_client_fs.audit_operation_list())


def _check_succeed(response: requests.Response):
    assert response.status_code in (200, 201), f'Request failed with code: {response.status_code}'


def _check_failed(response: requests.Response):
    assert response.status_code < 500, f'Request should not failed with 500: {response.json()}'
    assert response.status_code >= 400, f'Request was expected to be failed, but status code was {response.status_code}'
