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

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime as dt
from hashlib import md5
from logging import getLogger
from pathlib import Path
from shutil import rmtree
from tarfile import TarFile
from tempfile import mkdtemp
from time import sleep, time
from typing import NamedTuple
from urllib.parse import urlunparse

import requests
from audit.models import AuditLogOperationResult
from audit.utils import make_audit_log
from cm.adcm_config.config import get_adcm_config
from cm.models import ADCM, Bundle, Cluster, HostComponent, HostProvider
from django.conf import settings as adcm_settings
from django.core.management.base import BaseCommand
from django.db.models import Count, Prefetch, QuerySet
from rbac.models import Policy, Role, User
from rest_framework.status import HTTP_201_CREATED, HTTP_405_METHOD_NOT_ALLOWED


@dataclass
class ADCMData:
    uuid: str
    version: str


@dataclass
class BundleData:
    name: str
    version: str
    edition: str
    date: str


@dataclass
class HostComponentData:
    host_name: str
    component_name: str
    service_name: str


@dataclass
class ClusterData:
    name: str
    host_count: int
    bundle: dict
    host_component_map: list[dict]


@dataclass
class HostProviderData:
    name: str
    host_count: int
    bundle: dict


@dataclass
class UserData:
    email: str
    date_joined: str


@dataclass
class RoleData:
    name: str
    built_in: bool


class UrlComponents(NamedTuple):
    scheme: str
    netloc: str
    path: str
    params: str = ""
    query: str = ""
    fragment: str = ""


class RetryError(Exception):
    pass


logger = getLogger("background_tasks")


class StatisticsSettings:  # pylint: disable=too-many-instance-attributes
    def __init__(self):
        # pylint: disable=invalid-envvar-default

        adcm_uuid = str(ADCM.objects.get().uuid)

        self.enabled = self._get_enabled()

        self.url = self._get_url()
        self.headers = {"Adcm-UUID": adcm_uuid, "accept": "application/json"}
        self.timeout = 15

        self.retries_limit = int(os.getenv("STATISTICS_RETRIES", 10))
        self.retries_frequency = int(os.getenv("STATISTICS_FREQUENCY", 1 * 60 * 60))  # in seconds

        self.format_version = 0.1
        self.adcm_uuid = adcm_uuid

        self.date_format = "%Y-%m-%d %H:%M:%S"
        self.data_name = f"{dt.now().date().strftime('%Y_%m_%d')}_statistics"

    @staticmethod
    def _get_enabled() -> bool:
        if os.getenv("STATISTICS_ENABLED") is not None:
            return os.environ["STATISTICS_ENABLED"].upper() in {"1", "TRUE"}

        attr, _ = get_adcm_config(section="statistics_collection")
        return bool(attr["active"])

    @staticmethod
    def _get_url() -> str:
        url_path = "/api/v1/statistic/adcm"
        scheme = "http"

        if os.getenv("STATISTICS_URL") is not None:
            netloc = os.environ["STATISTICS_URL"]
        else:
            _, config = get_adcm_config(section="statistics_collection")
            netloc = config["url"]

        if len(splitted := netloc.split("://")) == 2:
            scheme = splitted[0]
            netloc = splitted[1]

        return urlunparse(components=UrlComponents(scheme=scheme, netloc=netloc, path=url_path))


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        self.settings = StatisticsSettings()
        super().__init__(*args, **kwargs)

    def handle(self, *args, **options):
        # pylint: disable=attribute-defined-outside-init
        try:
            self.tmp_dir = Path(mkdtemp()).absolute()
            self.main()
        except Exception:  # pylint: disable=broad-exception-caught
            self.log(msg="Unexpected error during statistics collection", method="exception")
        finally:
            rmtree(path=self.tmp_dir)

    def main(self):
        # pylint: disable=attribute-defined-outside-init
        if not self.settings.enabled:
            self.log(msg="disabled")
            return

        self.log(msg="started")
        make_audit_log(operation_type="statistics", result=AuditLogOperationResult.SUCCESS, operation_status="launched")

        for try_number in range(self.settings.retries_limit):
            self.last_try_timestamp = time()

            try:
                self.check_connection()
                archive_path = (self.tmp_dir / self.settings.data_name).with_suffix(".tar.gz")
                if not archive_path.is_file():
                    data = self.collect_statistics()
                    self.make_archive(target_path=archive_path, data=data)
                self.send_data(file_path=archive_path)
                make_audit_log(
                    operation_type="statistics", result=AuditLogOperationResult.SUCCESS, operation_status="completed"
                )
                break

            except RetryError:
                # skip last iteration sleep() call
                if try_number < self.settings.retries_limit - 1:
                    self.sleep()
        else:
            make_audit_log(
                operation_type="statistics", result=AuditLogOperationResult.FAIL, operation_status="completed"
            )

        self.log(msg="finished")

    def make_archive(self, target_path: Path, data: dict) -> None:
        json_path = (self.tmp_dir / self.settings.data_name).with_suffix(".json")
        with json_path.open(mode="w", encoding=adcm_settings.ENCODING_UTF_8) as json_file:
            json.dump(obj=data, fp=json_file)

        with TarFile.open(name=target_path, mode="w:gz", encoding=adcm_settings.ENCODING_UTF_8, compresslevel=9) as tar:
            tar.add(name=json_path, arcname=json_path.name)

        json_path.unlink()
        self.log(msg=f"archive created {target_path}")

    def collect_statistics(self) -> dict:
        self.log(msg="getting data...")
        community_bundles_qs = Bundle.objects.filter(edition="community")

        return {
            "adcm": asdict(ADCMData(uuid=self.settings.adcm_uuid, version=adcm_settings.ADCM_VERSION)),
            "format_version": self.settings.format_version,
            "data": {
                "clusters": self._get_clusters_data(bundles=community_bundles_qs),
                "bundles": self._get_bundles_data(bundles=community_bundles_qs),
                "providers": self._get_hostproviders_data(bundles=community_bundles_qs),
                "users": self._get_users_data(),
                "roles": self._get_roles_data(),
            },
        }

    def check_connection(self) -> None:
        """expecting 405 response on HEAD request without headers"""

        try:
            response = requests.head(url=self.settings.url, headers={}, timeout=self.settings.timeout)
        except requests.exceptions.ConnectionError as e:
            self.log(msg=f"error connecting to `{self.settings.url}`", method="exception")
            raise RetryError from e

        if response.status_code != HTTP_405_METHOD_NOT_ALLOWED:
            self.log(msg=f"Bad response: {response.status_code}`, HEAD {self.settings.url}`")
            raise RetryError

        self.log(msg="connection established")

    def send_data(self, file_path):
        self.log(msg="sending data...")
        with file_path.open(mode="rb") as archive:
            try:
                response = requests.post(
                    url=self.settings.url,
                    headers=self.settings.headers,
                    files={"file": archive},
                    timeout=self.settings.timeout,
                )
            except requests.exceptions.ConnectionError as e:
                self.log(msg=f"error connecting to `{self.settings.url}`", method="exception")
                raise RetryError from e

        if response.status_code != HTTP_201_CREATED:
            raise RetryError

        self.log(msg="data succesfully sent")

    def sleep(self):
        sleep_seconds = self.last_try_timestamp + self.settings.retries_frequency - time()
        sleep_seconds = max(sleep_seconds, 0)

        self.log(f"sleeping for {sleep_seconds} seconds")
        sleep(sleep_seconds)

    def log(self, msg: str, method: str = "debug") -> None:
        msg = f"Statistics collector: {msg}"
        self.stdout.write(msg)
        getattr(logger, method)(msg)

    @staticmethod
    def _get_roles_data() -> list[dict]:
        out_data = []

        for role_data in Role.objects.filter(
            pk__in=Policy.objects.filter(role__isnull=False).values_list("role_id", flat=True).distinct()
        ).values("name", "built_in"):
            out_data.append(asdict(RoleData(**role_data)))

        return out_data

    def _get_users_data(self) -> list[dict]:
        out_data = []
        for user_data in User.objects.values("email", "date_joined"):
            out_data.append(
                asdict(
                    UserData(
                        email=user_data["email"],
                        date_joined=user_data["date_joined"].strftime(self.settings.date_format),
                    )
                )
            )

        return out_data

    def _get_hostproviders_data(self, bundles: QuerySet[Bundle]) -> list[dict]:
        out_data = []
        for hostprovider in (
            HostProvider.objects.filter(prototype__bundle__in=bundles)
            .select_related("prototype__bundle")
            .annotate(host_count=Count("host"))
        ):
            out_data.append(
                asdict(
                    HostProviderData(
                        name=hostprovider.name,
                        host_count=hostprovider.host_count,
                        bundle=self._get_single_bundle_data(bundle=hostprovider.prototype.bundle),
                    )
                )
            )

        return out_data

    @staticmethod
    def _get_hostcomponent_data(cluster: Cluster) -> list[dict]:
        out_data = []
        for hostcomponent in cluster.hostcomponent_set.all():
            out_data.append(
                asdict(
                    HostComponentData(
                        host_name=md5(
                            hostcomponent.host.name.encode(encoding=adcm_settings.ENCODING_UTF_8)
                        ).hexdigest(),
                        component_name=hostcomponent.component.name,
                        service_name=hostcomponent.service.name,
                    )
                )
            )

        return out_data

    def _get_clusters_data(self, bundles: QuerySet[Bundle]) -> list[dict]:
        out_data = []
        for cluster in (
            Cluster.objects.filter(prototype__bundle__in=bundles)
            .select_related("prototype__bundle")
            .prefetch_related(
                Prefetch(
                    lookup="hostcomponent_set",
                    queryset=HostComponent.objects.select_related("host", "service", "component"),
                )
            )
            .annotate(host_count=Count("host"))
        ):
            out_data.append(
                asdict(
                    ClusterData(
                        name=cluster.name,
                        host_count=cluster.host_count,
                        bundle=self._get_single_bundle_data(bundle=cluster.prototype.bundle),
                        host_component_map=self._get_hostcomponent_data(cluster=cluster),
                    )
                )
            )

        return out_data

    def _get_single_bundle_data(self, bundle: Bundle) -> dict:
        return asdict(
            BundleData(
                name=bundle.name,
                version=bundle.version,
                edition=bundle.edition,
                date=bundle.date.strftime(self.settings.date_format),
            )
        )

    def _get_bundles_data(self, bundles: QuerySet[Bundle]) -> list[dict]:
        out_data = []
        for bundle in bundles:
            out_data.append(self._get_single_bundle_data(bundle=bundle))

        return out_data
