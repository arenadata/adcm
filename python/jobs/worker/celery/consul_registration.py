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

from __future__ import annotations

import re

from celery import bootsteps
from core.adcm import ADCMRepoI
from integrations.consul import ConsulBackend, ServiceRegistration

from jobs.scheduler.logger import logger
from jobs.worker.celery.custom import read_adcm_uuid

SERVICE_NAME = "adcm-worker"

_MIN_PASS_INTERVAL = 1.0
_DEFAULT_PASS_INTERVAL = 15.0
_DURATION_UNITS = {"s": 1, "m": 60, "h": 3600}


def build_worker_registration(
    *, hostname: str, datacenter: str | None, adcm_uuid: str | None, ttl: str, deregister_after: str
) -> ServiceRegistration:
    tags = [SERVICE_NAME]
    if adcm_uuid:
        tags.append(adcm_uuid)

    return ServiceRegistration(
        service_id=hostname,
        name=SERVICE_NAME,
        datacenter=datacenter,
        tags=tags,
        health_check_ttl=ttl,
        deregister_critical_service_after=deregister_after,
        check_id=_check_id(hostname),
    )


def ttl_refresh_interval(ttl: str) -> float:
    """Interval for refreshing a TTL check: half the TTL, so a single missed tick is not fatal."""
    matched = re.fullmatch(r"(\d+(?:\.\d+)?)([smh]?)", ttl.strip())
    if not matched:
        logger.warning("Cannot parse Consul TTL %r; refreshing every %ss", ttl, _DEFAULT_PASS_INTERVAL)
        return _DEFAULT_PASS_INTERVAL

    value, unit = matched.groups()
    seconds = float(value) * _DURATION_UNITS[unit or "s"]
    return max(seconds / 2, _MIN_PASS_INTERVAL)


class ConsulRegistrationStep(bootsteps.StartStopStep):
    """Register the worker as a ``celery`` service in Consul with a TTL health check."""

    requires = {"celery.worker.components:Timer"}

    def __init__(self, parent, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self.hostname = parent.hostname
        self._backend: ConsulBackend | None = None
        self._tref = None

    def start(self, parent) -> None:
        consul: ConsulBackend | None = parent.app.conf.consul
        if consul is None:
            logger.info("Consul is not configured; skipping worker registration")
            return

        adcm_uuid = read_adcm_uuid(parent.app.di_container.get(ADCMRepoI))
        ttl = consul.settings.health_check_ttl

        try:
            registration = build_worker_registration(
                hostname=self.hostname,
                datacenter=consul.settings.datacenter,
                adcm_uuid=adcm_uuid,
                ttl=ttl,
                deregister_after=consul.settings.deregister_critical_service_after,
            )
            consul.register(registration)
            # Report the TTL check right away so the service is healthy before the first tick.
            consul.pass_check(_check_id(self.hostname))
        except Exception:  # noqa: BLE001
            logger.exception("Failed to register worker %s in Consul", self.hostname)
            return

        self._backend = consul
        self._tref = parent.timer.call_repeatedly(
            secs=ttl_refresh_interval(ttl),
            fun=self._pass_check,
        )
        logger.info("Worker %s registered in Consul as %r service", self.hostname, SERVICE_NAME)

    def stop(self, parent) -> None:
        _ = parent
        if self._tref is not None:
            self._tref.cancel()
            self._tref = None

        if self._backend is not None:
            try:
                self._backend.deregister(self.hostname)
                logger.info("Worker %s deregistered from Consul", self.hostname)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to deregister worker %s from Consul", self.hostname)
            self._backend = None

    def _pass_check(self) -> None:
        if self._backend is None:
            return
        try:
            self._backend.pass_check(_check_id(self.hostname))
        except Exception:  # noqa: BLE001
            logger.exception("Failed to keep Consul TTL check alive for worker %s", self.hostname)


def _check_id(hostname: str) -> str:
    return f"service:{hostname}:ttl"
