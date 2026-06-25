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
Consul service registry integration for the ADCM backend.

:class:`ConsulBackend` is a process-wide singleton that owns a pooled
``requests.Session`` (so TCP/TLS connections are recycled) built from
:class:`ClientSettings`. It supports ACL token authentication as well as TLS /
mutual-TLS for ``https``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any, ClassVar

from requests import RequestException, Session
from requests.adapters import HTTPAdapter

DEFAULT_HEALTH_CHECK_INTERVAL = "10s"
DEFAULT_HEALTH_CHECK_TIMEOUT = "5s"
DEFAULT_DEREGISTER_CRITICAL_SERVICE_AFTER = "5m"
DEFAULT_HTTP_TIMEOUT = 5.0
DEFAULT_POOL_SIZE = 10


class ConsulError(RuntimeError):
    """Raised for unexpected Consul HTTP responses or transport errors."""


@dataclass(slots=True)
class ClientSettings:
    # main

    url: str
    datacenter: str | None = None
    acl_token: str | None = None

    # TLS / mTLS

    cacert_file: str | None = None
    client_cert_file: str | None = None
    client_key_file: str | None = None

    # transport tuning

    http_timeout: float = DEFAULT_HTTP_TIMEOUT
    pool_size: int = DEFAULT_POOL_SIZE


@dataclass(slots=True)
class ServiceRegistration:
    """Payload describing the ADCM service to register in Consul."""

    service_id: str
    address: str
    port: int
    health_check_url: str
    name: str
    datacenter: str | None = None
    tags: list[str] = field(default_factory=list)
    meta: dict[str, str] = field(default_factory=dict)
    check_interval: str = DEFAULT_HEALTH_CHECK_INTERVAL
    check_timeout: str = DEFAULT_HEALTH_CHECK_TIMEOUT
    deregister_critical_service_after: str = DEFAULT_DEREGISTER_CRITICAL_SERVICE_AFTER

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ID": self.service_id,
            "Name": self.name,
            "Tags": list(self.tags),
            "Address": self.address,
            "Port": self.port,
            "Meta": dict(self.meta),
            "Checks": [
                {
                    "HTTP": self.health_check_url,
                    "Interval": self.check_interval,
                    "Timeout": self.check_timeout,
                    "DeregisterCriticalServiceAfter": self.deregister_critical_service_after,
                }
            ],
        }
        if self.datacenter:
            payload["Datacenter"] = self.datacenter
        return payload


class ConsulBackend:
    """Process-wide Consul client owning a shared, TLS/token-aware HTTP session."""

    _instance: ClassVar[ConsulBackend | None] = None
    _lock: ClassVar[Lock] = Lock()

    def __init__(self, settings: ClientSettings) -> None:
        self._settings = settings
        self._base_url = settings.url.rstrip("/")
        self._timeout = settings.http_timeout

        session = Session()
        if settings.acl_token:
            session.headers["X-Consul-Token"] = settings.acl_token
        session.verify = settings.cacert_file if settings.cacert_file else True
        if settings.client_cert_file and settings.client_key_file:
            session.cert = (settings.client_cert_file, settings.client_key_file)
        adapter = HTTPAdapter(pool_connections=settings.pool_size, pool_maxsize=settings.pool_size)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        self._session = session

    @property
    def settings(self) -> ClientSettings:
        return self._settings

    @classmethod
    def initialize(cls, settings: ClientSettings) -> ConsulBackend:
        """Create (or replace) the shared backend instance."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
            cls._instance = cls(settings)
            return cls._instance

    @classmethod
    def instance(cls) -> ConsulBackend | None:
        """Return the shared backend instance or ``None`` if not initialized."""
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Drop the cached instance (closes its session)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
                cls._instance = None

    def register(self, registration: ServiceRegistration) -> None:
        url = f"{self._base_url}/v1/agent/service/register"
        try:
            response = self._session.put(
                url, params=self._query(), json=registration.to_payload(), timeout=self._timeout
            )
        except RequestException as error:
            raise ConsulError(f"Failed to register service in Consul: {error}") from error

        if not response.ok:
            raise ConsulError(
                f"Failed to register service in Consul: status={response.status_code} body={response.text!r}"
            )

    def deregister(self, service_id: str) -> None:
        url = f"{self._base_url}/v1/agent/service/deregister/{service_id}"
        try:
            response = self._session.put(url, params=self._query(), timeout=self._timeout)
        except RequestException as error:
            raise ConsulError(f"Failed to deregister service in Consul: {error}") from error

        if not response.ok:
            raise ConsulError(
                f"Failed to deregister service in Consul: status={response.status_code} body={response.text!r}"
            )

    def check_connection(self) -> bool:
        """Return ``True`` when the Consul agent is reachable and responsive."""
        url = f"{self._base_url}/v1/status/leader"
        try:
            response = self._session.get(url, params=self._query(), timeout=self._timeout)
        except RequestException:
            return False

        return response.ok

    def close(self) -> None:
        self._session.close()

    def _query(self) -> dict[str, str]:
        return {"dc": self._settings.datacenter} if self._settings.datacenter else {}
