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

from pathlib import Path
from unittest.mock import Mock, call, mock_open, patch

from api_v2.tests.base import BaseAPITestCase, ParallelReadyTestCase
from django.conf import settings
from django.core.management import load_command_class
from django.test import TestCase
from rbac.models import Policy, Role, User
from requests.exceptions import ConnectionError
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_405_METHOD_NOT_ALLOWED

from cm.collect_statistics.errors import RetriesExceededError, SenderConnectionError
from cm.collect_statistics.senders import SenderSettings, StatisticSender
from cm.models import ADCM, Bundle, ServiceComponent
from cm.tests.utils import gen_cluster, gen_provider


class TestStatistics(BaseAPITestCase):
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

        self.add_hostcomponent_map(
            cluster=self.cluster_1,
            hc_map=[
                {
                    "host_id": host_1.pk,
                    "service_id": service.pk,
                    "component_id": component_1.pk,
                },
                {
                    "host_id": host_2.pk,
                    "service_id": service.pk,
                    "component_id": component_1.pk,
                },
                {
                    "host_id": host_3.pk,
                    "service_id": service.pk,
                    "component_id": component_2.pk,
                },
            ],
        )

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

    def test_data_success(self):
        data = load_command_class(app_name="cm", name="collect_statistics").collect_statistics()
        expected_data = self._get_expected_data()

        self.assertDictEqual(data["adcm"], expected_data["adcm"])
        self.assertEqual(data["format_version"], expected_data["format_version"])

        self.assertListEqual(data["data"]["bundles"], expected_data["data"]["bundles"])
        self.assertListEqual(data["data"]["clusters"], expected_data["data"]["clusters"])
        self.assertListEqual(data["data"]["providers"], expected_data["data"]["providers"])
        self.assertListEqual(data["data"]["users"], expected_data["data"]["users"])
        self.assertListEqual(data["data"]["roles"], expected_data["data"]["roles"])


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
