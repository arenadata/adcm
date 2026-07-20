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

from unittest import TestCase
from unittest.mock import Mock, patch
import os

from application.di.providers.environment import ConsulSettings
from cm.legacy.status_api import status_service_url
from django.test import SimpleTestCase, override_settings
from integrations.consul import ServiceRegistration, url_with_base_path
from unittest_parametrize import ParametrizedTestCase, param, parametrize

from jobs.worker.celery.consul_registration import build_worker_registration, ttl_refresh_interval
from jobs.worker.celery.status_service import (
    StatusServiceUrlResolutionError,
    extract_status_service_url,
    resolve_external_status_service_url,
    setup_status_service_url,
)


class TestServiceRegistrationPayload(TestCase):
    def test_ttl_check_payload(self):
        registration = ServiceRegistration(
            service_id="celery@fe2db162d69b",
            name="celery",
            datacenter="dc1",
            tags=["adcm", "celery", "adcm-uuid"],
            health_check_ttl="30s",
            deregister_critical_service_after="5m",
            check_id="service:celery@fe2db162d69b:ttl",
        )

        payload = registration.to_payload()

        self.assertEqual(payload["ID"], "celery@fe2db162d69b")
        self.assertEqual(payload["Name"], "celery")
        self.assertEqual(payload["Datacenter"], "dc1")
        self.assertEqual(payload["Tags"], ["adcm", "celery", "adcm-uuid"])
        # a worker has no address / port to advertise
        self.assertNotIn("Address", payload)
        self.assertNotIn("Port", payload)
        self.assertEqual(
            payload["Checks"],
            [
                {
                    "TTL": "30s",
                    "DeregisterCriticalServiceAfter": "5m",
                    "CheckID": "service:celery@fe2db162d69b:ttl",
                }
            ],
        )

    def test_http_check_payload_still_supported(self):
        registration = ServiceRegistration(
            service_id="adcm@host",
            name="adcm",
            address="adcm.local",
            port=8000,
            health_check_url="http://adcm.local:8000/api/health/live",
            meta={"status_service_url": "http://adcm.local:8000/status/api/v1/"},
        )

        payload = registration.to_payload()

        self.assertEqual(payload["Address"], "adcm.local")
        self.assertEqual(payload["Port"], 8000)
        self.assertNotIn("Datacenter", payload)
        self.assertEqual(len(payload["Checks"]), 1)
        self.assertEqual(payload["Checks"][0]["HTTP"], "http://adcm.local:8000/api/health/live")
        self.assertNotIn("TTL", payload["Checks"][0])


class TestWorkerRegistration(ParametrizedTestCase, TestCase):
    def test_tags_include_uuid_when_present(self):
        registration = build_worker_registration(
            hostname="celery@node",
            datacenter="dc1",
            adcm_uuid="the-uuid",
            ttl="30s",
            deregister_after="5m",
        )

        self.assertEqual(registration.service_id, "celery@node")
        self.assertEqual(registration.name, "adcm-worker")
        self.assertEqual(registration.tags, ["adcm-worker", "the-uuid"])
        self.assertEqual(registration.health_check_ttl, "30s")
        self.assertEqual(registration.check_id, "service:celery@node:ttl")

    def test_tags_without_uuid(self):
        registration = build_worker_registration(
            hostname="celery@node",
            datacenter=None,
            adcm_uuid=None,
            ttl="30s",
            deregister_after="5m",
        )

        self.assertEqual(registration.tags, ["adcm-worker"])

    @parametrize(
        ("ttl", "expected"),
        [
            param("30s", 15.0, id="half_of_ttl"),
            param("2m", 60.0, id="minutes_unit"),
            param("1s", 1.0, id="clamped_to_minimum"),
            param("nonsense", 15.0, id="unparsable_falls_back_to_default"),
        ],
    )
    def test_ttl_refresh_interval(self, ttl: str, expected: float):
        self.assertEqual(ttl_refresh_interval(ttl), expected)


class TestConsulClientSettings(TestCase):
    @patch.dict(os.environ, {"CONSUL_URL": "http://localhost:8500"}, clear=True)
    def test_defaults(self):
        parsed = ConsulSettings().consul  # pyright: ignore[reportCallIssue]

        self.assertIsNone(parsed.datacenter)
        self.assertEqual(parsed.health_check_interval, "10s")
        self.assertEqual(parsed.health_check_timeout, "5s")
        self.assertEqual(parsed.health_check_ttl, "30s")
        self.assertEqual(parsed.deregister_critical_service_after, "5m")

    @patch.dict(
        os.environ,
        {
            "CONSUL_URL": "http://localhost:8500",
            "CONSUL_DATACENTER": "dc1",
            "CONSUL_HEALTH_CHECK_INTERVAL": "20s",
            "CONSUL_HEALTH_CHECK_TIMEOUT": "3s",
            "CONSUL_HEALTH_CHECK_TTL": "10s",
            "CONSUL_DEREGISTER_CRITICAL_SERVICE_AFTER": "1m",
        },
        clear=True,
    )
    def test_parsed_from_env(self):
        parsed = ConsulSettings().consul  # pyright: ignore[reportCallIssue]

        self.assertEqual(parsed.datacenter, "dc1")
        self.assertEqual(parsed.health_check_interval, "20s")
        self.assertEqual(parsed.health_check_timeout, "3s")
        self.assertEqual(parsed.health_check_ttl, "10s")
        self.assertEqual(parsed.deregister_critical_service_after, "1m")


class TestStatusServiceUrlResolution(ParametrizedTestCase, TestCase):
    @parametrize(
        ("entries", "expected"),
        [
            param(
                [{"Service": {"Meta": {"status_service_url": "http://adcm.local:8000/status/api/v1/"}}}],
                "http://adcm.local:8000/status/api/v1/",
                id="from_discovery",
            ),
            param(
                [
                    {"Service": {}},
                    {"Service": {"Meta": {}}},
                    {"Service": {"Meta": {"status_service_url": "http://second:8000/status/api/v1/"}}},
                ],
                "http://second:8000/status/api/v1/",
                id="skips_entries_without_meta",
            ),
            param([], None, id="none_when_absent"),
        ],
    )
    def test_extract_status_service_url(self, entries: list, expected: str | None):
        self.assertEqual(extract_status_service_url(entries), expected)

    @parametrize(
        ("url", "base_path", "expected"),
        [
            param(
                "http://adcm.local:8000",
                "/status/api/v1/",
                "http://adcm.local:8000/status/api/v1/",
                id="from_adcm_url",
            ),
            param(
                "http://adcm.local:8000/ui/foo?x=1",
                "status/api/v1/",
                "http://adcm.local:8000/status/api/v1/",
                id="strips_path_and_query",
            ),
            param("http://adcm.local:8000/ui", "", "http://adcm.local:8000", id="empty_base_path"),
        ],
    )
    def test_build_url_with_base_path(self, url: str, base_path: str, expected: str):
        self.assertEqual(url_with_base_path(url, base_path), expected)

    def test_resolve_prefers_consul_discovery(self):
        backend = Mock()
        backend.discover.return_value = [
            {"Service": {"Meta": {"status_service_url": "http://discovered:8000/status/api/v1/"}}}
        ]

        url = resolve_external_status_service_url(
            consul_backend=backend,
            adcm_uuid="the-uuid",
            default_adcm_url="http://fallback:8000",
            status_base_path="/status/api/v1/",
        )

        self.assertEqual(url, "http://discovered:8000/status/api/v1/")
        backend.discover.assert_called_once_with("adcm", tag="the-uuid")

    def test_resolve_falls_back_to_default_adcm_url_when_meta_missing(self):
        backend = Mock()
        backend.discover.return_value = [{"Service": {"Meta": {}}}]

        url = resolve_external_status_service_url(
            consul_backend=backend,
            adcm_uuid=None,
            default_adcm_url="http://fallback:8000",
            status_base_path="/status/api/v1/",
        )

        self.assertEqual(url, "http://fallback:8000/status/api/v1/")

    def test_resolve_falls_back_to_default_adcm_url_when_discovery_fails(self):
        backend = Mock()
        backend.discover.side_effect = RuntimeError("consul down")

        url = resolve_external_status_service_url(
            consul_backend=backend,
            adcm_uuid=None,
            default_adcm_url="http://fallback:8000",
            status_base_path="/status/api/v1/",
        )

        self.assertEqual(url, "http://fallback:8000/status/api/v1/")

    def test_resolve_without_consul_uses_default_adcm_url(self):
        url = resolve_external_status_service_url(
            consul_backend=None,
            adcm_uuid=None,
            default_adcm_url="http://fallback:8000",
            status_base_path="/status/api/v1/",
        )

        self.assertEqual(url, "http://fallback:8000/status/api/v1/")

    def test_resolve_returns_none_without_any_source(self):
        self.assertIsNone(
            resolve_external_status_service_url(
                consul_backend=None,
                adcm_uuid=None,
                default_adcm_url=None,
                status_base_path="/status/api/v1/",
            )
        )


class TestSetupStatusServiceUrl(TestCase):
    def setUp(self):
        # isolate the process-wide external URL override on the shared singleton
        patcher = patch.object(status_service_url, "external", None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_start_fails_when_url_cannot_be_resolved(self):
        parent = self._make_parent(consul=None, default_adcm_url=None)

        with self.assertRaises(StatusServiceUrlResolutionError):
            setup_status_service_url(sender=parent)

    def test_start_fails_when_discovery_is_empty_and_no_default_url(self):
        backend = Mock()
        backend.discover.return_value = []
        parent = self._make_parent(consul=backend, default_adcm_url=None)

        with self.assertRaises(StatusServiceUrlResolutionError):
            setup_status_service_url(sender=parent)

    def test_start_sets_external_url_when_resolved(self):
        parent = self._make_parent(consul=None, default_adcm_url="http://adcm.local:8000")

        setup_status_service_url(sender=parent)

        self.assertEqual(status_service_url.resolve(), "http://adcm.local:8000/status/api/v1/")

    @staticmethod
    def _make_parent(*, consul, default_adcm_url: str | None) -> Mock:
        parent = Mock()
        parent.app.conf.consul = consul
        parent.app.conf.default_adcm_url = default_adcm_url
        parent.app.conf.status_service_base_path = "/status/api/v1/"
        parent.app.di_container.get.return_value.get_uuid.return_value = "the-uuid"
        return parent


@override_settings(INTERNAL_STATUS_SERVICE_URL="http://localhost:8020/api/v1/")
class TestStatusApiBaseUrl(SimpleTestCase):
    def setUp(self):
        # isolate the process-wide external URL override on the shared singleton
        patcher = patch.object(status_service_url, "external", None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_internal_url_used_in_backend(self):
        self.assertEqual(status_service_url.resolve(), "http://localhost:8020/api/v1/")

    def test_external_url_preferred_when_resolved(self):
        status_service_url.set_external("http://adcm.local:8000/status/api/v1/")

        self.assertEqual(status_service_url.resolve(), "http://adcm.local:8000/status/api/v1/")
