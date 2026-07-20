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

"""Readiness checks used by the ``/api/health/ready`` endpoint.
Liveness checks used by the ``/api/health/live`` endpoint."""

from __future__ import annotations

from dataclasses import dataclass

from cm.logger import logger
from core import secrets
from core.scenarios.adcm import ADCMUUID
from django.db import OperationalError, connection
from django.db.migrations.executor import MigrationExecutor
from integrations.consul import ConsulBackend
from integrations.vault import VaultSecretsBackend

VAULT_SECRET_BACKEND = "VaultBackend"


@dataclass(slots=True, frozen=True)
class CheckResult:
    name: str
    healthy: bool
    detail: str = ""


def check_db_connectivity() -> CheckResult:
    try:
        connection.ensure_connection()
    except OperationalError:
        return CheckResult(name="database", healthy=False, detail="DB connectivity check failed")
    except Exception:  # noqa: BLE001
        logger.exception("DB connectivity check failed")
        return CheckResult(name="database", healthy=False, detail="DB connectivity check failed unexpectedly")

    return CheckResult(name="database", healthy=True)


def check_db_migrations() -> CheckResult:
    """
    Check that all migrations are applied.
    Returns a CheckResult with healthy=False if any migration is pending.
    """
    try:
        executor = MigrationExecutor(connection)
        # Get all migration plans
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            pending = len(plan)
            return CheckResult(
                name="migrations",
                healthy=False,
                detail=f"{pending} migration(s) pending",
            )
    except OperationalError:
        return CheckResult(name="migrations", healthy=False, detail="DB migration check failed")
    except Exception:  # noqa: BLE001
        logger.exception("DB migration check failed")
        return CheckResult(name="migrations", healthy=False, detail="DB migration check failed unexpectedly")

    return CheckResult(name="migrations", healthy=True, detail="")


def check_adcm_uuid(adcm_uuid: ADCMUUID | None) -> CheckResult:
    """Check that the ADCM UUID is configured."""
    if adcm_uuid is None:
        return CheckResult(name="adcm_uuid", healthy=False, detail="ADCM UUID is not configured")

    return CheckResult(name="adcm_uuid", healthy=True, detail="")


def check_vault(secrets_backend: secrets.SecretsBackend) -> CheckResult | None:
    """Check Vault connectivity, only when the Vault secret backend is configured."""
    if not isinstance(secrets_backend, VaultSecretsBackend):
        return None

    try:
        healthy = secrets_backend.check_connection()
    except Exception:  # noqa: BLE001
        logger.exception("Vault health check failed")
        return CheckResult(name="vault", healthy=False, detail="Vault health check failed unexpectedly")

    return CheckResult(name="vault", healthy=healthy, detail="" if healthy else "Vault is not reachable")


def check_consul(consul_backend: ConsulBackend | None) -> CheckResult | None:
    """Check Consul connectivity, only when the Consul backend is configured."""
    if consul_backend is None:
        return None

    try:
        healthy = consul_backend.check_connection()
    except Exception:  # noqa: BLE001
        logger.exception("Consul health check failed")
        return CheckResult(name="consul", healthy=False, detail="Consul health check failed unexpectedly")

    return CheckResult(name="consul", healthy=healthy, detail="" if healthy else "Consul is not reachable")


def run_readiness_checks(
    secrets_backend: secrets.SecretsBackend, consul_backend: ConsulBackend | None, adcm_uuid: ADCMUUID | None
) -> list[CheckResult]:
    return [
        check
        for check in (
            check_db_connectivity(),
            check_db_migrations(),
            check_adcm_uuid(adcm_uuid),
            check_vault(secrets_backend),
            check_consul(consul_backend),
        )
        if check is not None
    ]
