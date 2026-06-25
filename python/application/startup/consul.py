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
Startup wiring that registers the ADCM backend as a Consul service and
deregisters it on ``SIGINT`` / ``SIGTERM``.

Connection credentials, the ADCM URL and the ADCM uuid are resolved from the DI
container.

Registration is best-effort: any failure is logged and never aborts ADCM
startup, so an unreachable Consul agent does not prevent the backend from
serving requests.
"""

from __future__ import annotations

from urllib.parse import urlsplit
import socket

from cm.logger import logger
from core.adcm import ADCMRepoI
from core.scenarios.adcm import DefaultURL
from dishka import Container
from django.conf import settings
from integrations.consul import ClientSettings, ConsulBackend, ServiceRegistration


class ConsulConfigurationError(RuntimeError):
    """Raised when Consul-related configuration is inconsistent."""


def build_service_registration(*, datacenter: str | None, adcm_url: str, adcm_uuid: str | None) -> ServiceRegistration:
    parts = urlsplit(adcm_url)

    if parts.scheme is None or parts.hostname is None or parts.port is None:
        # adcm_url validation expected in previous steps, this is for type checking
        raise RuntimeError("Invalid adcm_url")

    base_url = f"{parts.scheme}://{parts.netloc}"
    container_id = socket.gethostname()

    status_service_base_path = settings.STATUS_SERVICE_BASE_PATH
    tags = ["adcm", "backend"]
    if adcm_uuid:
        tags.append(adcm_uuid)

    return ServiceRegistration(
        service_id=f"adcm@{container_id}",
        name="adcm",
        datacenter=datacenter,
        tags=tags,
        address=parts.hostname,
        port=parts.port,
        meta={"status_service_url": _join_url(base_url, status_service_base_path)},
        health_check_url=_join_url(base_url, "/api/health/live"),
        check_interval=settings.CONSUL_HEALTH_CHECK_INTERVAL,
        check_timeout=settings.CONSUL_HEALTH_CHECK_TIMEOUT,
        deregister_critical_service_after=settings.CONSUL_DEREGISTER_CRITICAL_SERVICE_AFTER,
    )


def register_adcm_in_service_discovery_when_consul_configured(container: Container) -> None:
    """Register ADCM in Consul (best-effort) using provided dependencies."""
    consul_backend = container.get(ConsulBackend | None)
    adcm_url = container.get(DefaultURL | None)
    adcm_uuid = container.get(ADCMRepoI).get_uuid()
    client_settings = container.get(ClientSettings | None)

    if client_settings is None:
        logger.info("Consul client settings not available; skipping registration")
        return

    if consul_backend is None:
        logger.info("Consul Backend not configured; skipping registration")
        return

    if adcm_url is None:
        logger.info("Skipping Consul registration: adcm_url is not set")
        return

    try:
        registration = build_service_registration(
            datacenter=client_settings.datacenter,
            adcm_url=str(adcm_url),
            adcm_uuid=adcm_uuid,
        )
        consul_backend.register(registration)
    except Exception:  # noqa: BLE001
        logger.error("Failed to register ADCM in Consul")
        return

    logger.info("ADCM registered in Consul as %s", registration.service_id)


def _join_url(base_url: str, path: str) -> str:
    if not path:
        return base_url
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"
