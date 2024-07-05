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

from hashlib import md5
from operator import itemgetter
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import Mock, call, mock_open, patch
import os
import json
import tarfile
import datetime

from adcm.tests.base import BaseTestCase, BusinessLogicMixin
from api_v2.tests.base import BaseAPITestCase, ParallelReadyTestCase
from django.conf import settings
from django.db.models import Q
from django.test import TestCase
from django.utils import timezone
from rbac.models import Policy, Role, User
from requests.exceptions import ConnectionError
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_405_METHOD_NOT_ALLOWED

from cm.collect_statistics.collectors import BundleCollector
from cm.collect_statistics.encoders import TarFileEncoder
from cm.collect_statistics.errors import RetriesExceededError, SenderConnectionError
from cm.collect_statistics.senders import SenderSettings, StatisticSender
from cm.collect_statistics.storages import JSONFile, StorageError, TarFileWithJSONFileStorage
from cm.models import ADCM, Bundle, ServiceComponent
from cm.tests.utils import gen_cluster, gen_provider


class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class TestSender(TestCase, ParallelReadyTestCase):
    maxDiff = None

    def setUp(self):
        self.settings = SenderSettings(
            url="https://www.test.url",
            adcm_uuid="TEST",
            retries_limit=2,
            retries_frequency=0,
            request_timeout=0.1,
        )

    @patch.object(target=Path, attribute="open", new_callable=mock_open())
    @patch("cm.collect_statistics.senders.requests")
    def test_success(self, mocked_requests, mocked_open):
        mocked_requests.head.return_value = MockResponse(status_code=HTTP_405_METHOD_NOT_ALLOWED)
        mocked_requests.post.return_value = MockResponse(status_code=HTTP_201_CREATED)

        sender = StatisticSender(settings=self.settings)
        sender.send(targets=[Path("/some/path.file"), Path("/other/path.file")])

        self.assertEqual(mocked_open.call_count, 2)

        mocked_requests.head.assert_called_once_with(
            url=self.settings.url, headers={}, timeout=self.settings.request_timeout
        )

        self.assertEqual(mocked_requests.post.call_count, 2)
        self.assertListEqual(
            mocked_requests.post.call_args_list,
            [
                call(
                    url=self.settings.url,
                    headers={"Adcm-UUID": "TEST", "accept": "application/json"},
                    files={"file": mocked_open().__enter__()},
                    timeout=self.settings.request_timeout,
                )
            ]
            * 2,
        )

    @patch("cm.collect_statistics.senders.requests")
    def test_connection_fail(self, mocked_requests):
        sender = StatisticSender(settings=self.settings)

        mocked_requests.head.return_value = MockResponse(status_code=HTTP_200_OK)

        with self.assertRaises(expected_exception=SenderConnectionError) as err_status:
            sender.send(targets=[Path("/some/path.file")])
        self.assertEqual(
            str(err_status.exception), f"Check connection: wrong return code for {self.settings.url}: {HTTP_200_OK}"
        )

        mocked_requests.head.return_value = MockResponse(status_code=HTTP_405_METHOD_NOT_ALLOWED)
        mocked_requests.head = Mock(side_effect=ConnectionError)

        with self.assertRaises(expected_exception=SenderConnectionError) as err_post:
            sender.send(targets=[Path("/some/path.file")])
        self.assertEqual(str(err_post.exception), f"Check connection: can't connect to {self.settings.url}")

    @patch.object(target=Path, attribute="open", new_callable=mock_open())
    @patch("cm.collect_statistics.senders.requests")
    def test_retries_fail(self, mocked_requests, mocked_open):  # noqa: ARG002
        mocked_requests.head.return_value = MockResponse(status_code=HTTP_405_METHOD_NOT_ALLOWED)
        mocked_requests.post = Mock(side_effect=ConnectionError)

        sender = StatisticSender(settings=self.settings)
        with self.assertRaises(expected_exception=RetriesExceededError) as err_retries:
            sender.send(targets=[Path("/some/path.file")])
        self.assertEqual(
            str(err_retries.exception), f"None of the {self.settings.retries_limit} attempts was successful"
        )

    @patch.object(target=Path, attribute="open", new_callable=mock_open())
    @patch("cm.collect_statistics.senders.requests")
    def test_retry_only_failed(self, mocked_requests, mocked_open):  # noqa: ARG002
        mocked_requests.head.return_value = MockResponse(status_code=HTTP_405_METHOD_NOT_ALLOWED)
        mocked_requests.post.side_effect = [
            MockResponse(status_code=HTTP_201_CREATED),
            MockResponse(status_code=0),
            MockResponse(status_code=HTTP_201_CREATED),
        ]

        file_1, file_2 = Path("/some/path.file"), Path("/other/path.file")

        sender = StatisticSender(settings=self.settings)
        with patch.object(target=sender, attribute="_send", wraps=sender._send) as mocked_inner_send:
            sender.send(targets=[file_1, file_2])

        self.assertListEqual(
            mocked_inner_send.call_args_list, [call(target=file_1), call(target=file_2), call(target=file_2)]
        )


class TestBundleCollector(BaseTestCase, BusinessLogicMixin):
    def setUp(self) -> None:
        super().setUp()

        self.bundles_dir = Path(__file__).parent / "bundles"
        self.maxDiff = None

    def test_collect_community_bundle_collector(self) -> None:
        # prepare data
        bundle_cluster_reg = self.add_bundle(self.bundles_dir / "cluster_1")
        bundle_cluster_full = self.add_bundle(self.bundles_dir / "cluster_full_config")
        bundle_prov_reg = self.add_bundle(self.bundles_dir / "provider")
        bundle_prov_full = self.add_bundle(self.bundles_dir / "provider_full_config")

        cluster_reg_1 = self.add_cluster(bundle=bundle_cluster_reg, name="Regular 1")
        cluster_full = self.add_cluster(bundle=bundle_cluster_full, name="Full 1")
        cluster_reg_2 = self.add_cluster(bundle=bundle_cluster_reg, name="Regular 2")

        provider_full_1 = self.add_provider(bundle=bundle_prov_full, name="Prov Full 1")
        provider_full_2 = self.add_provider(bundle=bundle_prov_full, name="Prov Full 2")
        provider_reg_1 = self.add_provider(bundle=bundle_prov_reg, name="Prov Reg 1")

        host_1 = self.add_host(provider=provider_full_1, fqdn="host-1", cluster=cluster_reg_1)
        host_2 = self.add_host(provider=provider_full_1, fqdn="host-2", cluster=cluster_reg_2)
        self.add_host(provider=provider_reg_1, fqdn="host-3", cluster=cluster_reg_1)

        self.add_services_to_cluster(["service_one_component"], cluster=cluster_reg_1)
        service_2 = self.add_services_to_cluster(["service_two_components"], cluster=cluster_reg_1).get()
        service_3 = self.add_services_to_cluster(["service_two_components"], cluster=cluster_reg_2).get()

        component_1, component_2 = service_2.servicecomponent_set.order_by("id").all()
        component_3 = service_3.servicecomponent_set.order_by("id").first()
        self.set_hostcomponent(cluster=cluster_reg_1, entries=((host_1, component_1), (host_1, component_2)))

        self.set_hostcomponent(cluster=cluster_reg_2, entries=((host_2, component_3),))

        # prepare expected
        order_hc_by = itemgetter("component_name")
        by_name = itemgetter("name")
        collect = BundleCollector(date_format="%Y", filters=[Q(edition="community")])
        current_year = str(timezone.now().year)
        host_1_name_hash = md5(host_1.fqdn.encode("utf-8")).hexdigest()  # noqa: S324
        host_2_name_hash = md5(host_2.fqdn.encode("utf-8")).hexdigest()  # noqa: S324
        expected_bundles = [
            {"name": bundle.name, "version": bundle.version, "edition": "community", "date": current_year}
            for bundle in (
                bundle_cluster_reg,
                bundle_cluster_full,
                bundle_prov_reg,
                bundle_prov_full,
                Bundle.objects.get(name="ADCM"),
            )
        ]
        expected = {
            "bundles": sorted(expected_bundles, key=by_name),
            "providers": sorted(
                [
                    {"name": provider_full_1.name, "bundle": expected_bundles[3], "host_count": 2},
                    {"name": provider_full_2.name, "bundle": expected_bundles[3], "host_count": 0},
                    {"name": provider_reg_1.name, "bundle": expected_bundles[2], "host_count": 1},
                ],
                key=by_name,
            ),
            "clusters": sorted(
                [
                    {
                        "name": cluster_full.name,
                        "host_count": 0,
                        "bundle": expected_bundles[1],
                        "host_component_map": [],
                    },
                    {
                        "name": cluster_reg_1.name,
                        "host_count": 2,
                        "bundle": expected_bundles[0],
                        "host_component_map": sorted(
                            [
                                {
                                    "host_name": host_1_name_hash,
                                    "component_name": component_1.name,
                                    "service_name": service_2.name,
                                },
                                {
                                    "host_name": host_1_name_hash,
                                    "component_name": component_2.name,
                                    "service_name": service_2.name,
                                },
                            ],
                            key=order_hc_by,
                        ),
                    },
                    {
                        "name": cluster_reg_2.name,
                        "host_count": 1,
                        "bundle": expected_bundles[0],
                        "host_component_map": [
                            {
                                "host_name": host_2_name_hash,
                                "component_name": component_3.name,
                                "service_name": service_3.name,
                            },
                        ],
                    },
                ],
                key=by_name,
            ),
        }

        # check
        actual = collect().model_dump()

        # order for reproducible comparison
        for root_key in actual:
            actual[root_key] = sorted(actual[root_key], key=by_name)

        for entry in actual["clusters"]:
            entry["host_component_map"] = sorted(entry["host_component_map"], key=order_hc_by)

        self.assertDictEqual(actual, expected)


class TestStorage(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.maxDiff = None

        enterprise_bundle_cluster = Bundle.objects.create(
            name="enterprise_cluster", version="1.0", edition="enterprise"
        )
        enterprise_bundle_provider = Bundle.objects.create(
            name="enterprise_provider", version="1.2", edition="enterprise"
        )

        gen_cluster(name="enterprise_cluster", bundle=enterprise_bundle_cluster)
        gen_provider(name="enterprise_provider", bundle=enterprise_bundle_provider)

        adcm_user_role = Role.objects.get(name="ADCM User")
        Policy.objects.create(name="test policy", role=adcm_user_role, built_in=False)

        host_1 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_1")
        host_2 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_2")
        host_3 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_3")
        host_unmapped = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_unmapped")
        self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_not_in_cluster")

        for host in (host_1, host_2, host_3, host_unmapped):
            self.add_host_to_cluster(cluster=self.cluster_1, host=host)

        service = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        component_1 = ServiceComponent.objects.get(
            cluster=self.cluster_1, service=service, prototype__name="component_1"
        )
        component_2 = ServiceComponent.objects.get(
            cluster=self.cluster_1, service=service, prototype__name="component_2"
        )

        self.set_hostcomponent(
            cluster=self.cluster_1, entries=[(host_1, component_1), (host_2, component_1), (host_3, component_2)]
        )

        self.expected_data = self._get_expected_data()

    @staticmethod
    def _get_expected_data() -> dict:
        date_fmt = "%Y-%m-%d %H:%M:%S"

        users = [
            {
                "date_joined": User.objects.get(username="admin").date_joined.strftime(date_fmt),
                "email": "admin@example.com",
            },
            {"date_joined": User.objects.get(username="status").date_joined.strftime(date_fmt), "email": ""},
            {"date_joined": User.objects.get(username="system").date_joined.strftime(date_fmt), "email": ""},
        ]

        bundles = [
            {
                "name": "ADCM",
                "version": Bundle.objects.get(name="ADCM").version,
                "edition": "community",
                "date": Bundle.objects.get(name="ADCM").date.strftime(date_fmt),
            },
            {
                "name": "cluster_one",
                "version": "1.0",
                "edition": "community",
                "date": Bundle.objects.get(name="cluster_one").date.strftime(date_fmt),
            },
            {
                "name": "cluster_two",
                "version": "1.0",
                "edition": "community",
                "date": Bundle.objects.get(name="cluster_two").date.strftime(date_fmt),
            },
            {
                "name": "provider",
                "version": "1.0",
                "edition": "community",
                "date": Bundle.objects.get(name="provider").date.strftime(date_fmt),
            },
        ]

        clusters = [
            {
                "name": "cluster_1",
                "host_count": 4,
                "bundle": {
                    "name": "cluster_one",
                    "version": "1.0",
                    "edition": "community",
                    "date": Bundle.objects.get(name="cluster_one").date.strftime(date_fmt),
                },
                "host_component_map": [
                    {
                        "host_name": "379679191547aa70b797855c744bf684",
                        "component_name": "component_1",
                        "service_name": "service_1",
                    },
                    {
                        "host_name": "889214cc620857cbf83f2ccc0c190162",
                        "component_name": "component_1",
                        "service_name": "service_1",
                    },
                    {
                        "host_name": "11ee6e2ffdb6fd444dab9ad0a1fbda9d",
                        "component_name": "component_2",
                        "service_name": "service_1",
                    },
                ],
            },
            {
                "name": "cluster_2",
                "host_count": 0,
                "bundle": {
                    "name": "cluster_two",
                    "version": "1.0",
                    "edition": "community",
                    "date": Bundle.objects.get(name="cluster_two").date.strftime(date_fmt),
                },
                "host_component_map": [],
            },
        ]

        providers = [
            {
                "bundle": {
                    "date": Bundle.objects.get(name="provider").date.strftime(date_fmt),
                    "edition": "community",
                    "name": "provider",
                    "version": "1.0",
                },
                "host_count": 5,
                "name": "provider",
            }
        ]

        roles = [{"built_in": True, "name": "ADCM User"}]

        return {
            "adcm": {"uuid": str(ADCM.objects.get().uuid), "version": settings.ADCM_VERSION},
            "data": {
                "bundles": bundles,
                "clusters": clusters,
                "providers": providers,
                "roles": roles,
                "users": users,
            },
            "format_version": 0.1,
        }

    def read_tar(self, path: Path) -> list[dict]:
        content = []
        with tarfile.open(path) as tar:
            for member in tar.getmembers():
                with tar.extractfile(member) as f:
                    content.append(json.loads(f.read()))
        return content

    def test_storage_one_file_success(self):
        community_storage = TarFileWithJSONFileStorage()
        expected_name = (
            f"{datetime.datetime.now(tz=datetime.timezone.utc).date().strftime('%Y-%m-%d')}_statistics.tar.gz"
        )

        community_storage.add(
            JSONFile(
                filename="data.json",
                data=self.expected_data,
            )
        )
        community_archive = community_storage.gather()
        self.assertTrue(community_archive.exists())
        self.assertTrue(community_archive.is_file())
        self.assertTrue(community_archive.suffixes == [".tar", ".gz"])
        self.assertEqual(community_archive.name, expected_name)

        self.assertListEqual(self.read_tar(community_archive), [self.expected_data])

    def test_storage_archive_written_twice_success(self):
        community_storage = TarFileWithJSONFileStorage()
        expected_name = (
            f"{datetime.datetime.now(tz=datetime.timezone.utc).date().strftime('%Y-%m-%d')}_statistics.tar.gz"
        )

        community_storage.add(
            JSONFile(
                filename="data.json",
                data=self.expected_data,
            )
        )
        community_archive = community_storage.gather()
        self.assertEqual(community_archive.name, expected_name)
        self.assertListEqual(self.read_tar(community_archive), [self.expected_data])

        community_archive = community_storage.gather()
        self.assertEqual(community_archive.name, expected_name)
        self.assertListEqual(self.read_tar(community_archive), [self.expected_data])

    def test_storage_several_files_success(self):
        full_stat = [self.expected_data, self.expected_data, self.expected_data]

        community_storage = TarFileWithJSONFileStorage()

        for data in full_stat:
            community_storage.add(
                JSONFile(
                    filename="data.json",
                    data=data,
                )
            )
        community_archive = community_storage.gather()

        for content, expected_data in zip(self.read_tar(community_archive), full_stat):
            self.assertDictEqual(content, expected_data)

    def test_storage_clear_fail(self):
        community_storage = TarFileWithJSONFileStorage()
        community_storage.add(
            JSONFile(
                filename="data.json",
                data=self.expected_data,
            )
        )
        community_storage.clear()
        with self.assertRaises(StorageError):
            community_storage.gather()

    def test_storage_empty_json_fail(self):
        community_storage = TarFileWithJSONFileStorage()
        community_storage.add(
            JSONFile(
                filename="data.json",
                data={},
            )
        )
        with self.assertRaises(StorageError):
            community_storage.gather()

    def test_no_intermediate_files_created(self):
        community_storage = TarFileWithJSONFileStorage()

        json_file = JSONFile(
            filename="data.json",
            data=self.expected_data,
        )

        community_storage.add(json_file)
        community_archive = community_storage.gather()
        self.assertFalse(community_archive.is_dir())
        self.assertFalse(os.path.exists(json_file.filename))


class TestEncoder(TestCase, ParallelReadyTestCase):
    def test_uncorrected_suffix(self):
        with self.assertRaises(ValueError) as error:
            TarFileEncoder(suffix="enc")

        self.assertEqual(str(error.exception), "Invalid suffix 'enc'")

    def test_uncorrected_filename(self):
        with self.assertRaises(ValueError) as error:
            encoder = TarFileEncoder(suffix=".enc")
            encoder.decode(Path("test.tar.gz"))

        self.assertEqual(str(error.exception), "The file name must end with '.enc'")

    def test_encode(self):
        path_file = Path(NamedTemporaryFile(suffix=".tar.gz").name)
        path_file.write_text("content")

        encoder = TarFileEncoder(suffix=".enc")
        encoded_file = encoder.encode(path_file=path_file)

        self.assertTrue(encoded_file.exists())
        self.assertTrue(encoded_file.is_file())
        self.assertTrue(encoded_file.suffix == ".enc")
        self.assertTrue(encoded_file.read_bytes() == b"dpoufou")

    def test_decode(self):
        encoded_file = Path(NamedTemporaryFile(suffix=".tar.gz.enc").name)
        encoded_file.write_bytes(b"dpoufou")

        encoder = TarFileEncoder(suffix=".enc")
        decoded_file = encoder.decode(path_file=encoded_file)

        self.assertTrue(decoded_file.exists())
        self.assertTrue(decoded_file.is_file())
        self.assertTrue(decoded_file.suffixes == [".tar", ".gz"])
        self.assertTrue(decoded_file.read_bytes() == b"content")

    def test_encode_decode(self):
        path_file = Path(NamedTemporaryFile(suffix=".tar.gz").name)
        path_file.write_text("content")

        encoder = TarFileEncoder(suffix=".enc")
        encoded_file = encoder.encode(path_file=path_file)
        decoded_file = encoder.decode(path_file=encoded_file)

        self.assertTrue(decoded_file.exists())
        self.assertTrue(decoded_file.is_file())
        self.assertTrue(decoded_file.suffixes, [".tar", ".gz"])
        self.assertTrue(decoded_file.read_bytes() == b"content")
