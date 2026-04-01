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

from contextlib import suppress
from pathlib import Path
from tempfile import gettempdir
from typing import Collection, TypeAlias
import uuid
import tarfile

from cm.legacy.services.cluster import retrieve_cluster_topology, retrieve_clusters_objects_maintenance_mode
from cm.models import (
    Action,
    ActionHostGroup,
    Bundle,
    Cluster,
    Component,
    ConfigHostGroup,
    Host,
    MaintenanceMode,
    ObjectType,
    Process,
    Prototype,
    Provider,
    Service,
)
from core.legacy.cluster.operations import calculate_maintenance_mode_for_cluster_objects
from core.legacy.cluster.types import ObjectMaintenanceModeState
from core.types import ClusterID
from rbac.models import Group, Policy, Role, User
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from tests.client import ADCMTestClient, APINode

AuditTarget: TypeAlias = (
    Bundle | Cluster | Service | Component | ActionHostGroup | Provider | Host | User | Group | Role | Policy
)

TEST_BUNDLES_DIR = Path(__file__).parent / "bundles"
TEST_FILES_DIR = Path(__file__).parent / "files"

# allow asserts
# ruff: noqa: S101


class APIV2Mixin:
    client: ADCMTestClient

    def _prepare_bundle_file(self, src: Path, dst: Path) -> Path:
        with tarfile.open(dst, "w") as tar:
            for file in src.iterdir():
                tar.add(name=file, arcname=file.name)

        return dst

    def create_bundle(self, src: Path) -> Bundle:
        if not src.is_dir():
            raise ValueError(f"Not a dir: {src}")

        # shouldn't be required, tempdir must be unique,
        # yet I don't want to create new tempdir for each call
        # => universal mechanism is required
        random_suffix = uuid.uuid4().hex[:8]

        # note that gettempdir doesn't return unique directory
        dst = Path(gettempdir(), f"{src.name}-{random_suffix}").with_suffix(".tar")
        archive = self._prepare_bundle_file(src=src, dst=dst)

        with archive.open(mode="rb") as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        if response.status_code != HTTP_201_CREATED:
            reason = "unknown"
            with suppress(Exception):
                reason = response.json()

            message = f"Bundle `{archive}` upload failed ({response.status_code=}) with reason: {reason}"
            raise RuntimeError(message)

        return Bundle.objects.get(id=response.json()["id"])

    def create_cluster(self, bundle: Bundle, name: str, description: str = "", accept_license: bool = True) -> Cluster:
        prototype = Prototype.objects.only("id", "license").get(bundle=bundle, type=ObjectType.CLUSTER)
        if prototype.license == "unaccepted" and accept_license:
            response = self.client.v2[prototype, "license", "accept"].post()
            assert response.status_code == HTTP_200_OK, f"Accept license failed: {response.status_code}"

        response = (self.client.v2 / "clusters").post(
            data={"prototypeId": prototype.id, "name": name, "description": description}
        )
        assert response.status_code == HTTP_201_CREATED, f"Cluster creation failed: {response.status_code}"

        return Cluster.objects.get(id=response.json()["id"])

    def create_services(self, names: Collection[str], cluster: Cluster) -> list[Service]:
        bundle_id = cluster.prototype.bundle_id
        prototype_ids = Prototype.objects.values_list("id", flat=True).filter(
            name__in=names, type=ObjectType.SERVICE, bundle_id=bundle_id
        )
        response = self.client.v2[cluster, "services"].post(data=[{"prototype_id": id_} for id_ in prototype_ids])
        assert response.status_code == HTTP_201_CREATED, f"Service creation failed: {response.status_code}"

        return list(Service.objects.filter(id__in=[r["id"] for r in response.json()]))

    def create_mapping(self, cluster: Cluster, entries: Collection[tuple[Host, Component]]) -> None:
        response = self.client.v2[cluster, "mapping"].post(
            data=[{"hostId": host.id, "componentId": component.id} for host, component in entries]
        )
        assert response.status_code == HTTP_201_CREATED, f"Mapping creation failed: {response.status_code}"

    def create_provider(self, bundle: Bundle, name: str, description: str = "") -> Provider:
        prototype_id = Prototype.objects.values_list("id", flat=True).get(bundle=bundle, type=ObjectType.PROVIDER)
        response = (self.client.v2 / "hostproviders").post(
            data={"prototypeId": prototype_id, "name": name, "description": description},
        )
        assert response.status_code == HTTP_201_CREATED, f"Provider creation failed: {response.status_code}"

        return Provider.objects.get(id=response.json()["id"])

    def create_host(self, provider: Provider, name: str, cluster: Cluster | None = None) -> Host:
        data = {"hostproviderId": provider.id, "name": name}
        if cluster:
            data["clusterId"] = cluster.id
        response = (self.client.v2 / "hosts").post(data=data)
        assert response.status_code == HTTP_201_CREATED, f"Host creation failed: {response.status_code}"

        return Host.objects.get(id=response.json()["id"])

    def create_action_host_group(
        self, owner: Cluster | Service | Component, name: str, hosts: Collection[Host] = (), description: str = ""
    ) -> ActionHostGroup:
        response = self.client.v2[owner, "action-host-groups"].post(data={"name": name, "description": description})
        assert response.status_code == HTTP_201_CREATED, f"ActionHostGroup creation failed: {response.status_code}"

        ahg = ActionHostGroup.objects.get(id=response.json()["id"])

        for host in hosts:
            response = self.client.v2[ahg, "hosts"].post(data={"hostId": host.id})
            assert response.status_code == HTTP_201_CREATED, f"Add host to {ahg} failed: {response.status_code}"

        return ahg

    def create_config_host_group(
        self,
        owner: Cluster | Service | Component | Provider | Host,
        name: str,
        hosts: Collection[Host] = (),
        description: str = "",
    ) -> ConfigHostGroup:
        response = self.client.v2[owner, "config-groups"].post(data={"name": name, "description": description})
        assert response.status_code == HTTP_201_CREATED, f"ConfigHostGroup creation failed: {response.status_code}"

        chg = ConfigHostGroup.objects.get(id=response.json()["id"])

        for host in hosts:
            response = self.client.v2[chg, "hosts"].post(data={"hostId": host.id})
            assert response.status_code == HTTP_201_CREATED, f"Add host to {chg} failed: {response.status_code}"

        return chg

    def set_maintenance_mode(self, obj: Service | Component | Host, value: MaintenanceMode) -> None:
        response = self.client.v2[obj, "maintenance-mode"].post(data={"maintenance_mode": value})
        assert response.status_code == HTTP_200_OK, f"Setting maintenance mode failed: {response.status_code}"

    # wizard

    def start_process_r(
        self,
        target: Cluster | Service | Component | Host,
        action: Action | int,
        *,
        expected_status: int = HTTP_201_CREATED,
    ):
        action_id = self._resolve_action_id(action)
        object_endpoint = self._resolve_wizard_object_endpoint(target)
        response = (object_endpoint / "actions" / action_id / "processes").post(data={})
        self.assertEqual(
            response.status_code,
            expected_status,
            self._response_error(response=response, expected_code=expected_status),
        )
        return response

    def submit_step_r(
        self,
        target: Cluster | Service | Component | Host,
        action: Action | int,
        process_id: int,
        data: dict,
        *,
        expected_status: int = HTTP_200_OK,
    ):
        action_id = self._resolve_action_id(action)
        object_endpoint = self._resolve_wizard_object_endpoint(target=target)
        response = (object_endpoint / "actions" / action_id / "processes" / process_id / "operation").post(data=data)
        self.assertEqual(
            response.status_code,
            expected_status,
            self._response_error(response=response, expected_code=expected_status),
        )
        return response

    def get_process_r(
        self,
        target: Cluster | Service | Component | Host,
        action: Action | int,
        process_id: int,
        *,
        expected_status: int = HTTP_200_OK,
    ):
        action_id = self._resolve_action_id(action)
        object_endpoint = self._resolve_wizard_object_endpoint(target)
        response = (object_endpoint / "actions" / action_id / "processes" / process_id).get()
        self.assertEqual(
            response.status_code,
            expected_status,
            self._response_error(response=response, expected_code=expected_status),
        )
        return response

    def get_step_r(
        self,
        target: Cluster | Service | Component | Host,
        action: Action | int,
        process_id: int,
        step_id: int,
        *,
        expected_status: int = HTTP_200_OK,
    ):
        action_id = self._resolve_action_id(action)
        object_endpoint = self._resolve_wizard_object_endpoint(target=target)
        response = (object_endpoint / "actions" / action_id / "processes" / process_id / "steps" / step_id).get()
        self.assertEqual(
            response.status_code,
            expected_status,
            self._response_error(response=response, expected_code=expected_status),
        )
        return response

    def start_process(self, owner: Cluster | Service | Component | Host, action: Action | int) -> Process:
        response = self.start_process_r(target=owner, action=action)
        return Process.objects.get(id=response.json()["id"])

    def submit_step(
        self, owner: Cluster | Service | Component | Host, action: Action | int, process_id: int, data: dict
    ) -> Process:
        response = self.submit_step_r(target=owner, action=action, process_id=process_id, data=data)
        return Process.objects.get(id=response.json()["id"])

    def _resolve_wizard_object_endpoint(self, target: Cluster | Service | Component | Host) -> APINode:
        if isinstance(target, Host):
            return self.client.v2[target.cluster, "hosts", target]

        return self.client.v2[target]

    @staticmethod
    def _resolve_action_id(action: Action | int) -> int:
        if isinstance(action, Action):
            return action.id

        if isinstance(action, int):
            return action

        # keep it here until tests are somehow typechecked
        raise TypeError(f"Unexpected action type: {type(action)}")

    @staticmethod
    def _response_error(response, expected_code: int) -> str:
        try:
            details = response.json()
        except Exception:  # noqa: BLE001 - best-effort error reporting
            details = response.content

        return f"Expected response code {expected_code}, got {response.status_code}. " f"Response details: {details}"


class TestUtilsMixin:
    def check_mm_is_on_only_for(self, obj: Component | Host | None, cluster_id: ClusterID):
        objects_mm = calculate_maintenance_mode_for_cluster_objects(
            topology=retrieve_cluster_topology(cluster_id=cluster_id),
            own_maintenance_mode=retrieve_clusters_objects_maintenance_mode(cluster_ids=(cluster_id,)),
        )
        components_mm = objects_mm.components
        hosts_mm = objects_mm.hosts

        if isinstance(obj, Component):
            self.assertEqual(components_mm.pop(obj.id), ObjectMaintenanceModeState.ON)
        elif isinstance(obj, Host):
            self.assertEqual(hosts_mm.pop(obj.id), ObjectMaintenanceModeState.ON)
        elif obj is None:
            pass
        else:
            raise ValueError(f"Unexpected object type: {type(obj)}")

        self.assertSetEqual(set(objects_mm.services.values()), {ObjectMaintenanceModeState.OFF})
        self.assertSetEqual(set(components_mm.values()), {ObjectMaintenanceModeState.OFF})
        self.assertSetEqual(set(hosts_mm.values()), {ObjectMaintenanceModeState.OFF})
