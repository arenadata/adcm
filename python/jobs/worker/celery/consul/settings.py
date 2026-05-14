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
Configuration for the Consul KV storage backend used by Celery's custom
control/inspect commands.

All values are resolved from environment variables with sensible defaults.
"""

from __future__ import annotations

import os


def _getenv(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def _getfloat(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as err:
        raise RuntimeError(f"Environment variable {name!r} must be a number, got {raw!r}") from err


def _getint(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as err:
        raise RuntimeError(f"Environment variable {name!r} must be an integer, got {raw!r}") from err


# Consul server connection. CONSUL_URL / CONSUL_DATACENTER / CONSUL_CACERT_FILE
CONSUL_URL: str | None = _getenv("CONSUL_URL")
CONSUL_DATACENTER: str | None = _getenv("CONSUL_DATACENTER")
CONSUL_CACERT_FILE: str | None = _getenv("CONSUL_CACERT_FILE")
CONSUL_ACL_TOKEN: str | None = _getenv("CONSUL_ACL_TOKEN")
CONSUL_HTTP_TIMEOUT: float = _getfloat("CONSUL_HTTP_TIMEOUT", 5.0)
# Maximum number of HTTP connections kept alive inside the shared session pool.
CONSUL_HTTP_POOL_SIZE: int = _getint("CONSUL_HTTP_POOL_SIZE", 10)

# KV paths.
CONSUL_KV_COMMAND_PREFIX: str | None = _getenv("CONSUL_KV_COMMAND_PREFIX", "celery/command")
CONSUL_KV_RESPONSE_PREFIX: str | None = _getenv("CONSUL_KV_RESPONSE_PREFIX", "celery/response")

# Polling intervals (seconds).
# - Command: worker polls `CONSUL_KV_COMMAND_PREFIX/*` to pick up new commands.
# - Response: control/inspect client polls `CONSUL_KV_RESPONSE_PREFIX/<cmd_id>/*`
#   to collect per-worker responses until the timeout is reached.
CONSUL_KV_COMMAND_POLL_INTERVAL: float = _getfloat("CONSUL_KV_COMMAND_POLL_INTERVAL", 1.0)
CONSUL_KV_RESPONSE_POLL_INTERVAL: float = _getfloat("CONSUL_KV_RESPONSE_POLL_INTERVAL", 0.5)


def is_enabled() -> bool:
    """Return True if all mandatory settings for Consul-based control are set."""
    return bool(CONSUL_URL and CONSUL_KV_COMMAND_PREFIX and CONSUL_KV_RESPONSE_PREFIX)


def normalize_prefix(prefix: str) -> str:
    """Normalize a KV prefix: strip leading slash, ensure trailing slash."""
    return prefix.lstrip("/").rstrip("/") + "/"
