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

"""Tests for imports"""
from typing import Optional

import allure
import pytest
import requests
from adcm_client.objects import ADCMClient, Cluster

from tests.functional.audit.conftest import (
    BUNDLES_DIR,
    NEW_USER,
    check_failed,
    check_succeed,
    make_auth_header,
    parametrize_audit_scenario_parsing,
)
from tests.functional.audit.test_objects_updates import EXPORT_SERVICE, IMPORT_SERVICE
from tests.functional.rbac.conftest import BusinessRoles, create_policy

# pylint: disable=redefined-outer-name


@pytest.fixture()
def import_export_clusters(sdk_client_fs) -> tuple[Cluster, Cluster]:
    """Create clusters from import and export bundles and add services to them"""
    import_bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / "incorrect_import_export" / "import")
    import_cluster = import_bundle.cluster_create("Import")
    import_cluster.service_add(name=IMPORT_SERVICE)
    export_bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / "incorrect_import_export" / "export")
    export_cluster = export_bundle.cluster_create("Export")
    export_cluster.service_add(name=EXPORT_SERVICE)
    return import_cluster, export_cluster


def bind(url: str, cluster_id: Optional[int], service_id: Optional[int], **kwargs) -> requests.Response:
    body = {
        **({"export_cluster_id": cluster_id} if cluster_id else {}),
        **({"export_service_id": service_id} if service_id else {}),
    }

    with allure.step(f"Create bind via POST {url} with body: {body}"):
        return requests.post(url, json=body, **kwargs)


def change_service_id(
    admin_client: ADCMClient, user_client: ADCMClient, import_cluster: Cluster, export_cluster: Cluster
) -> None:
    """Set different service id and send request"""
    export_service = export_cluster.service()
    import_service = import_cluster.service()
    url = f"{admin_client.url}/api/v1/cluster/{import_cluster.id}/service/{import_service.id}/bind/"

    with allure.step(
        f"Bind cluster and service with wrong service id {(export_service.id + 1)}," " with admin header and wait fail"
    ):
        check_failed(
            bind(
                url=url,
                cluster_id=export_cluster.id,
                service_id=(export_service.id + 1),
                headers=make_auth_header(admin_client),
            ),
            exact_code=404,
        )

    with allure.step(
        f"Bind cluster and service with wrong service id {(export_service.id + 1)}," " with user header and wait fail"
    ):
        check_failed(
            bind(
                url=url,
                cluster_id=export_cluster.id,
                service_id=(export_service.id + 1),
                headers=make_auth_header(user_client),
            ),
            exact_code=403,
        )

    with allure.step("Bind cluster and service with empty service id, with admin header and wait fail"):
        check_failed(
            bind(url=url, cluster_id=export_cluster.id, service_id=None, headers=make_auth_header(admin_client)),
            exact_code=404,
        )

    with allure.step("Bind cluster and service with empty service id, with user header and wait fail"):
        check_failed(
            bind(url=url, cluster_id=export_cluster.id, service_id=None, headers=make_auth_header(user_client)),
            exact_code=403,
        )


def change_import_url(
    admin_client: ADCMClient, user_client: ADCMClient, import_cluster: Cluster, export_cluster: Cluster
) -> None:
    """Set different url and send request"""
    export_service = export_cluster.service()
    import_service = import_cluster.service()

    bind_from_cluster_url = f"{admin_client.url}/api/v1/cluster/{import_cluster.id}/service/{import_service.id}/bind/"
    bind_from_service_url = f"{admin_client.url}/api/v1/service/{import_service.id}/bind/"

    with allure.step(f"Bind cluster and service with url {bind_from_cluster_url} with admin header and wait success"):
        check_succeed(
            bind(
                url=bind_from_cluster_url,
                cluster_id=export_cluster.id,
                service_id=export_service.id,
                headers=make_auth_header(admin_client),
            )
        )

    with allure.step(f"Unbind service with url {bind_from_service_url}"):
        service_bind_id = requests.get(bind_from_cluster_url, headers=make_auth_header(admin_client)).json()[0]["id"]
        check_succeed(
            requests.delete(f"{bind_from_cluster_url}{service_bind_id}/", headers=make_auth_header(admin_client))
        )

    with allure.step(f"Bind cluster and service with url {bind_from_service_url} with admin header and wait success"):
        check_succeed(
            bind(
                url=bind_from_service_url,
                cluster_id=export_cluster.id,
                service_id=export_service.id,
                headers=make_auth_header(admin_client),
            )
        )

    with allure.step(f"Bind cluster and service with url {bind_from_cluster_url} with user header and wait fail"):
        check_failed(
            bind(
                url=bind_from_cluster_url,
                cluster_id=export_cluster.id,
                service_id=export_service.id,
                headers=make_auth_header(user_client),
            ),
            exact_code=403,
        )

    with allure.step(f"Bind cluster and service with url {bind_from_service_url} with user header and wait fail"):
        check_failed(
            bind(
                url=bind_from_service_url,
                cluster_id=export_cluster.id,
                service_id=export_service.id,
                headers=make_auth_header(user_client),
            ),
            exact_code=403,
        )


@parametrize_audit_scenario_parsing("import_audit.yaml", NEW_USER)
def test_negative_service_import(sdk_client_fs: ADCMClient, new_user_client, audit_log_checker, import_export_clusters):
    """Test to check params on import"""
    import_cluster, export_cluster = import_export_clusters
    import_service = import_cluster.service()
    new_user = sdk_client_fs.user(id=new_user_client.me().id)
    create_policy(sdk_client_fs, [BusinessRoles.VIEW_SERVICE_CONFIGURATIONS], [import_service], [new_user], [])

    change_import_url(
        admin_client=sdk_client_fs,
        user_client=new_user_client,
        import_cluster=import_cluster,
        export_cluster=export_cluster,
    )

    change_service_id(
        admin_client=sdk_client_fs,
        user_client=new_user_client,
        import_cluster=import_cluster,
        export_cluster=export_cluster,
    )

    audit_log_checker.set_user_map(sdk_client_fs)
    audit_log_checker.check(list(sdk_client_fs.audit_operation_list()))
