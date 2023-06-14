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

import random
import string
from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree

from cm.models import (
    ADCM,
    ADCMEntity,
    Bundle,
    Cluster,
    ClusterObject,
    ConfigLog,
    Host,
    HostProvider,
    ObjectType,
    Prototype,
    ServiceComponent,
)
from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse
from init_db import init
from rbac.models import Role, RoleTypes, User
from rbac.upgrade.role import init_roles
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

APPLICATION_JSON = "application/json"


class BaseTestCase(TestCase):
    # pylint: disable=too-many-instance-attributes,too-many-public-methods

    def setUp(self) -> None:
        self.test_user_username = "test_user"
        self.test_user_password = "test_user_password"

        self.test_user = User.objects.create_user(
            username=self.test_user_username,
            password=self.test_user_password,
            is_superuser=True,
        )

        self.no_rights_user_username = "no_rights_user"
        self.no_rights_user_password = "no_rights_user_password"
        self.no_rights_user = User.objects.create_user(
            username="no_rights_user",
            password="no_rights_user_password",
        )

        self.client = Client(HTTP_USER_AGENT="Mozilla/5.0")
        self.login()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        init_roles()
        init()

        adcm = ADCM.objects.first()
        config_log = ConfigLog.objects.get(obj_ref=adcm.config)
        config_log.config["auth_policy"]["max_password_length"] = 20
        config_log.save(update_fields=["config"])

    def tearDown(self) -> None:
        dirs_to_clear = (
            *Path(settings.BUNDLE_DIR).iterdir(),
            *Path(settings.DOWNLOAD_DIR).iterdir(),
            *Path(settings.FILE_DIR).iterdir(),
            *Path(settings.LOG_DIR).iterdir(),
            *Path(settings.RUN_DIR).iterdir(),
        )
        for item in dirs_to_clear:
            if item.is_dir():
                rmtree(item)
            else:
                if item.name != ".gitkeep":
                    item.unlink()

    def login(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={"username": self.test_user_username, "password": self.test_user_password},
            content_type=APPLICATION_JSON,
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"

    @property
    @contextmanager
    def no_rights_user_logged_in(self):
        self.client.post(path=reverse(viewname="v1:rbac:logout"))
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={
                "username": self.no_rights_user_username,
                "password": self.no_rights_user_password,
            },
            content_type=APPLICATION_JSON,
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"

        yield

        self.login()

    @contextmanager
    def another_user_logged_in(self, username: str, password: str):
        self.client.post(path=reverse(viewname="v1:rbac:logout"))
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={
                "username": username,
                "password": password,
            },
            content_type=APPLICATION_JSON,
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"

        yield

        self.login()

    def another_user_log_in(self, username: str, password: str):
        self.client.post(path=reverse(viewname="v1:rbac:logout"))
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={
                "username": username,
                "password": password,
            },
            content_type=APPLICATION_JSON,
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"

    def get_new_user(self, username: str, password: str, group_pk: int | None = None) -> User:
        data = {"username": username, "password": password}
        if group_pk:
            data["group"] = [{"id": group_pk}]

        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:user-list"),
            data=data,
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return User.objects.get(pk=response.json()["id"])

    def get_role_data(self, role_name: str) -> dict:
        response: Response = self.client.get(
            path=reverse(viewname="v1:rbac:role-list"),
            data={"name": role_name, "type": "role", "view": "interface"},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        return response.json()["results"][0]

    def create_policy(
        self,
        role_name: str,
        obj: ADCMEntity,
        user_pk: int | None = None,
        group_pk: int | None = None,
    ) -> int:
        role_data = self.get_role_data(role_name=role_name)

        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:policy-list"),
            data={
                "name": f"test_policy_{obj.prototype.type}_{obj.pk}_admin",
                "role": {"id": role_data["id"]},
                "user": [{"id": user_pk}] if user_pk else [],
                "group": [{"id": group_pk}] if group_pk else [],
                "object": [{"name": obj.name, "type": obj.prototype.type, "id": obj.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return response.json()["id"]

    def create_role(
        self,
        role_name: str,
        parametrized_by_type: list[ObjectType],
        children_names: list[str],
    ) -> Role:
        request_data = {
            "name": role_name,
            "display_name": role_name,
            "type": RoleTypes.ROLE,
            "parametrized_by_type": parametrized_by_type,
            "child": [],
        }
        for child_name in children_names:
            response: Response = self.client.get(
                path=reverse(viewname="v1:rbac:role-list"),
                data={"name": child_name},
                content_type=APPLICATION_JSON,
            )

            self.assertEqual(response.status_code, HTTP_200_OK)

            request_data["child"].append({"id": response.json()["results"][0]["id"]})

        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:role-list"),
            data=request_data,
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return Role.objects.get(pk=response.json()["id"])

    def upload_bundle(self, path: Path) -> None:
        with open(path, encoding=settings.ENCODING_UTF_8) as f:
            response: Response = self.client.post(
                path=reverse(viewname="v1:upload-bundle"),
                data={"file": f},
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def load_bundle(self, path: Path) -> Bundle:
        response: Response = self.client.post(
            path=reverse(viewname="v1:load-bundle"),
            data={"bundle_file": path.name},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        return Bundle.objects.get(pk=response.data["id"])

    def upload_and_load_bundle(self, path: Path) -> Bundle:
        self.upload_bundle(path=path)

        return self.load_bundle(path=path)

    def create_cluster(self, bundle_pk: int, name: str) -> Cluster:
        response: Response = self.client.post(
            path=reverse(viewname="v1:cluster"),
            data={
                "prototype_id": Prototype.objects.get(bundle_id=bundle_pk, type=ObjectType.CLUSTER).pk,
                "name": name,
                "display_name": name,
                "bundle_id": bundle_pk,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return Cluster.objects.get(pk=response.json()["id"])

    def create_service(self, cluster_pk: int, name: str) -> ClusterObject:
        response = self.client.post(
            path=reverse(viewname="v1:service", kwargs={"cluster_id": cluster_pk}),
            data={"prototype_id": Prototype.objects.get(name=name).pk},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return ClusterObject.objects.get(pk=response.json()["id"])

    def upload_bundle_create_cluster_config_log(
        self, bundle_path: Path, cluster_name: str = "test-cluster"
    ) -> tuple[Bundle, Cluster, ConfigLog]:
        bundle = self.upload_and_load_bundle(path=bundle_path)
        cluster = self.create_cluster(bundle_pk=bundle.pk, name=cluster_name)

        return bundle, cluster, ConfigLog.objects.get(obj_ref=cluster.config)

    def create_provider(self, bundle_path: Path, name: str) -> HostProvider:
        bundle = self.upload_and_load_bundle(path=bundle_path)

        response: Response = self.client.post(
            path=reverse(viewname="v1:provider"),
            data={
                "prototype_id": Prototype.objects.get(bundle=bundle, type=ObjectType.PROVIDER).pk,
                "name": name,
                "display_name": name,
                "bundle_id": bundle.pk,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return HostProvider.objects.get(pk=response.json()["id"])

    def create_host_in_cluster(self, provider_pk: int, name: str, cluster_pk: int) -> Host:
        response: Response = self.client.post(
            path=reverse(viewname="v1:host", kwargs={"provider_id": provider_pk}),
            data={"fqdn": name},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host = Host.objects.get(pk=response.json()["id"])

        response: Response = self.client.post(
            path=reverse(viewname="v1:host", kwargs={"cluster_id": cluster_pk}),
            data={"host_id": host.pk},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return host

    def add_host_to_cluster(self, cluster_pk: int, host_pk: int) -> None:
        response: Response = self.client.post(
            path=reverse(viewname="v1:host", kwargs={"cluster_id": cluster_pk}),
            data={"host_id": host_pk},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    @staticmethod
    def get_hostcomponent_data(service_pk: int, host_pk: int) -> list[dict[str, int]]:
        hostcomponent_data = []
        for component in ServiceComponent.objects.filter(service_id=service_pk):
            hostcomponent_data.append({"component_id": component.pk, "host_id": host_pk, "service_id": service_pk})

        return hostcomponent_data

    def create_hostcomponent(self, cluster_pk: int, hostcomponent_data: list[dict[str, int]]):
        response: Response = self.client.post(
            path=reverse(viewname="v1:host-component", kwargs={"cluster_id": cluster_pk}),
            data={"cluster_id": cluster_pk, "hc": hostcomponent_data},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    @staticmethod
    def get_random_str_num(length: int) -> str:
        return "".join(random.sample(f"{string.ascii_letters}{string.digits}", length))
