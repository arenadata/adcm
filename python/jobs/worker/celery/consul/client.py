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
Thin HTTP client for the Consul KV endpoints used by the custom Celery
control/inspect transport.

Recycle TCP/TLS connections instead of opening a new one for every operation.
The client itself is a process-wide singleton;
callers obtain it via :func:`get_consul_kv_client`.

TLS and ACL options are picked up from environment/settings so that both
ACL (token) and TLS (CA file) based hardening are supported out of the box.
"""

from __future__ import annotations

from base64 import b64decode, b64encode
from threading import Lock
from typing import Any, ClassVar
import json as jsonlib

from requests import Session
from requests.adapters import HTTPAdapter

from jobs.worker.celery.consul import settings as consul_settings


class ConsulKVError(RuntimeError):
    """Raised for any unexpected Consul KV HTTP response."""


class ConsulKVClient:
    """
    Minimal Consul KV client with pooled HTTP connections.

    Only the endpoints required by the control/inspect transport are
    exposed: :meth:`put`, :meth:`get`, :meth:`list_keys`, :meth:`list_pairs`
    and :meth:`delete`.
    """

    _KV_PATH = "/v1/kv"

    def __init__(
        self,
        *,
        base_url: str,
        datacenter: str | None = None,
        token: str | None = None,
        verify: str | bool = True,
        timeout: float = 5.0,
        pool_size: int = 10,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._datacenter = datacenter
        self._timeout = timeout

        session = Session()
        if token:
            session.headers["X-Consul-Token"] = token
        session.verify = verify
        # Reuse the same pool of TCP connections across all kv requests.
        adapter = HTTPAdapter(pool_connections=pool_size, pool_maxsize=pool_size)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        self._session = session

    def put(self, key: str, value: Any) -> None:
        """Store ``value`` at ``key``. ``value`` is json-encoded automatically."""
        url = f"{self._base_url}{self._KV_PATH}/{_clean(key)}"
        response = self._session.put(
            url,
            params=self._query(),
            data=_encode_value(value),
            timeout=self._timeout,
        )
        if not response.ok or response.text.strip() != "true":
            raise ConsulKVError(
                f"Failed to PUT consul kv {key!r}: status={response.status_code} body={response.text!r}"
            )

    def get(self, key: str) -> Any | None:
        """Fetch the value at ``key`` or ``None`` if it does not exist."""
        url = f"{self._base_url}{self._KV_PATH}/{_clean(key)}"
        response = self._session.get(url, params=self._query(), timeout=self._timeout)
        if response.status_code == 404:
            return None
        if not response.ok:
            raise ConsulKVError(
                f"Failed to GET consul kv {key!r}: status={response.status_code} body={response.text!r}"
            )
        payload = response.json()
        if not payload:
            return None
        return _decode_value(payload[0].get("Value"))

    def list_keys(self, prefix: str) -> list[str]:
        """Return the full list of keys under ``prefix`` (recursive)."""
        url = f"{self._base_url}{self._KV_PATH}/{_clean(prefix)}"
        response = self._session.get(url, params=self._query(keys="true"), timeout=self._timeout)
        if response.status_code == 404:
            return []
        if not response.ok:
            raise ConsulKVError(
                f"Failed to LIST consul kv {prefix!r}: status={response.status_code} body={response.text!r}"
            )
        data = response.json()
        return list(data) if data else []

    def list_pairs(self, prefix: str) -> dict[str, Any]:
        """Return ``{key: value}`` for every key under ``prefix`` (recursive)."""
        url = f"{self._base_url}{self._KV_PATH}/{_clean(prefix)}"
        response = self._session.get(url, params=self._query(recurse="true"), timeout=self._timeout)
        if response.status_code == 404:
            return {}
        if not response.ok:
            raise ConsulKVError(
                f"Failed to RECURSE consul kv {prefix!r}: status={response.status_code} body={response.text!r}"
            )
        payload = response.json() or []
        return {entry["Key"]: _decode_value(entry.get("Value")) for entry in payload}

    def delete(self, key: str, *, recurse: bool = False) -> None:
        """Delete ``key`` (or everything under it when ``recurse`` is true)."""
        url = f"{self._base_url}{self._KV_PATH}/{_clean(key)}"
        params = self._query()
        if recurse:
            params["recurse"] = "true"
        response = self._session.delete(url, params=params, timeout=self._timeout)
        if not response.ok:
            raise ConsulKVError(
                f"Failed to DELETE consul kv {key!r}: status={response.status_code} body={response.text!r}"
            )

    def close(self) -> None:
        self._session.close()

    def _query(self, **extra: str) -> dict[str, str]:
        params: dict[str, str] = {}
        if self._datacenter:
            params["dc"] = self._datacenter
        params.update(extra)
        return params


def _encode_value(value: Any) -> bytes:
    return jsonlib.dumps(value, ensure_ascii=False, default=str).encode("utf-8")


def _decode_value(raw: str | None) -> Any | None:
    if raw is None:
        return None
    decoded = b64decode(raw).decode("utf-8")
    try:
        return jsonlib.loads(decoded)
    except jsonlib.JSONDecodeError:
        return decoded


def _clean(key: str) -> str:
    return key.lstrip("/")


__all__ = [
    "ConsulKVClient",
    "ConsulKVError",
    "b64encode",
    "get_consul_kv_client",
    "reset_consul_kv_client",
]


_client_lock = Lock()


class _ConsulClientRegistry:
    _instance: ClassVar[ConsulKVClient | None] = None

    @classmethod
    def get(cls) -> ConsulKVClient:
        if cls._instance is not None:
            return cls._instance
        with _client_lock:
            if cls._instance is None:
                cls._instance = _build_client()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        with _client_lock:
            if cls._instance is not None:
                cls._instance.close()
                cls._instance = None


def _build_client() -> ConsulKVClient:
    if not consul_settings.CONSUL_URL:
        raise ConsulKVError("CONSUL_URL is not set: Consul-based Celery control transport cannot be used.")

    verify: str | bool = True
    if consul_settings.CONSUL_CACERT_FILE:
        verify = consul_settings.CONSUL_CACERT_FILE

    return ConsulKVClient(
        base_url=consul_settings.CONSUL_URL,
        datacenter=consul_settings.CONSUL_DATACENTER,
        token=consul_settings.CONSUL_ACL_TOKEN,
        verify=verify,
        timeout=consul_settings.CONSUL_HTTP_TIMEOUT,
        pool_size=consul_settings.CONSUL_HTTP_POOL_SIZE,
    )


def get_consul_kv_client() -> ConsulKVClient:
    """
    Return the process-wide :class:`ConsulKVClient` instance.
    """
    return _ConsulClientRegistry.get()


def reset_consul_kv_client() -> None:
    """Drop the cached client (mostly useful for tests)."""
    _ConsulClientRegistry.reset()
