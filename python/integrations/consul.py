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

:class:`ConsulBackend` owns a pooled ``requests.Session`` (so TCP/TLS
connections are recycled) built from :class:`ClientSettings`. It supports ACL
token authentication as well as TLS / mutual-TLS for ``https``. Its lifecycle
is managed by the DI container (one APP-scoped instance).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from requests import RequestException, Session
from requests.adapters import HTTPAdapter

DEFAULT_HEALTH_CHECK_INTERVAL = "10s"
DEFAULT_HEALTH_CHECK_TIMEOUT = "5s"
DEFAULT_HEALTH_CHECK_TTL = "30s"
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

    # service registration health check tuning

    health_check_interval: str = DEFAULT_HEALTH_CHECK_INTERVAL
    health_check_timeout: str = DEFAULT_HEALTH_CHECK_TIMEOUT
    health_check_ttl: str = DEFAULT_HEALTH_CHECK_TTL
    deregister_critical_service_after: str = DEFAULT_DEREGISTER_CRITICAL_SERVICE_AFTER

    # transport tuning

    http_timeout: float = DEFAULT_HTTP_TIMEOUT
    pool_size: int = DEFAULT_POOL_SIZE


@dataclass(slots=True)
class ServiceRegistration:
    """Payload describing a service (ADCM backend or Celery worker) to register in Consul.
    Two health check flavours are supported:
    * an HTTP check (``health_check_url``) - Consul polls the endpoint itself;
    * a TTL check (``health_check_ttl``) - the service keeps the check alive by
      periodically calling :meth:`ConsulBackend.pass_check`."""

    service_id: str
    name: str
    address: str | None = None
    port: int | None = None
    datacenter: str | None = None
    tags: list[str] = field(default_factory=list)
    meta: dict[str, str] = field(default_factory=dict)
    # HTTP check
    health_check_url: str | None = None
    check_interval: str = DEFAULT_HEALTH_CHECK_INTERVAL
    check_timeout: str = DEFAULT_HEALTH_CHECK_TIMEOUT
    # TTL check (takes precedence over the HTTP check when set)
    health_check_ttl: str | None = None
    check_id: str | None = None
    deregister_critical_service_after: str = DEFAULT_DEREGISTER_CRITICAL_SERVICE_AFTER

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ID": self.service_id,
            "Name": self.name,
            "Tags": list(self.tags),
            "Meta": dict(self.meta),
            "Checks": [self._build_check()],
        }
        if self.address is not None:
            payload["Address"] = self.address
        if self.port is not None:
            payload["Port"] = self.port
        if self.datacenter:
            payload["Datacenter"] = self.datacenter
        return payload

    def _build_check(self) -> dict[str, Any]:
        if self.health_check_ttl is not None:
            check: dict[str, Any] = {
                "TTL": self.health_check_ttl,
                "DeregisterCriticalServiceAfter": self.deregister_critical_service_after,
            }
        else:
            check = {
                "HTTP": self.health_check_url,
                "Interval": self.check_interval,
                "Timeout": self.check_timeout,
                "DeregisterCriticalServiceAfter": self.deregister_critical_service_after,
            }
        if self.check_id:
            check["CheckID"] = self.check_id
        return check


def url_with_base_path(url: str, base_path: str) -> str:
    """``scheme://netloc`` of `url` joined with `base_path` (any path of `url` is dropped)."""
    parts = urlsplit(url)
    base_url = f"{parts.scheme}://{parts.netloc}"
    if not base_path:
        return base_url
    return f"{base_url.rstrip('/')}/{base_path.lstrip('/')}"


class ConsulBackend:
    """Consul client owning a pooled, TLS/token-aware HTTP session."""

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

    def discover(self, name: str, *, tag: str | None = None, passing_only: bool = True) -> list[dict[str, Any]]:
        """Return health service entries registered in Consul under ``name``."""
        url = f"{self._base_url}/v1/health/service/{name}"
        params = self._query()
        if passing_only:
            params["passing"] = "true"
        if tag:
            params["tag"] = tag

        try:
            response = self._session.get(url, params=params, timeout=self._timeout)
        except RequestException as error:
            raise ConsulError(f"Failed to discover service {name!r} in Consul: {error}") from error

        if not response.ok:
            raise ConsulError(
                f"Failed to discover service {name!r} in Consul: status={response.status_code} body={response.text!r}"
            )

        return response.json() or []

    def pass_check(self, check_id: str, *, note: str | None = None) -> None:
        """Mark a TTL check as passing, keeping the associated service healthy."""
        url = f"{self._base_url}/v1/agent/check/pass/{check_id}"
        params = self._query()
        if note:
            params["note"] = note

        try:
            response = self._session.put(url, params=params, timeout=self._timeout)
        except RequestException as error:
            raise ConsulError(f"Failed to pass Consul check {check_id!r}: {error}") from error

        if not response.ok:
            raise ConsulError(
                f"Failed to pass Consul check {check_id!r}: status={response.status_code} body={response.text!r}"
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
