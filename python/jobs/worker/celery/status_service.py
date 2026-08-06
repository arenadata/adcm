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

from typing import Any
import logging

from celery.signals import worker_init
from cm.legacy.status_api import status_service_url
from core.adcm import ADCMRepoI
from integrations.consul import ConsulBackend, url_with_base_path

from jobs.worker.celery.custom import read_adcm_uuid

logger = logging.getLogger("adcm.worker")

ADCM_SERVICE_NAME = "adcm"
STATUS_SERVICE_URL_META = "status_service_url"


class StatusServiceUrlResolutionError(Exception):
    ...


def extract_status_service_url(entries: list[dict[str, Any]]) -> str | None:
    """
    Pick the ``status_service_url`` meta from the first ADCM discovery entry that has one.

    With several ADCM instances registered under the same uuid tag, any of
    their advertised URLs is considered equivalent (they front the same status
    service), so first-non-empty is a deliberate rule, not an accident.
    """
    for entry in entries:
        meta = (entry.get("Service") or {}).get("Meta") or {}
        url = meta.get(STATUS_SERVICE_URL_META)
        if url:
            return url

    return None


def resolve_external_status_service_url(
    *,
    consul_backend: ConsulBackend | None,
    adcm_uuid: str | None,
    default_adcm_url: str | None,
    status_base_path: str,
) -> str | None:
    if consul_backend is not None:
        url = _discover_status_service_url(backend=consul_backend, adcm_uuid=adcm_uuid)
        if url:
            return url

    if default_adcm_url:
        # consul-less fallback: same formula the backend uses to build the URL
        # it advertises in Consul meta (see application.startup.consul); when
        # discovery works, the advertised URL above wins — it is authoritative
        # for scheme and base path
        return url_with_base_path(default_adcm_url, status_base_path)

    return None


def setup_status_service_url(sender, **_) -> None:
    """Point ``status_api`` at the resolved external status service URL on worker start.

    Wired to ``worker_init``, not a bootstep: the prefork pool forks its
    children while the worker blueprint is being built, before any bootstep's
    ``start`` runs, so a URL set from a bootstep exists only in the main
    process and every pool child falls back to the internal URL. worker_init
    fires in the main process before the blueprint (and thus the pool) is
    created, so the resolved URL is inherited by every forked child.
    """
    conf = sender.app.conf
    resolved_url = resolve_external_status_service_url(
        consul_backend=conf.consul,
        adcm_uuid=read_adcm_uuid(sender.app.di_container.get(ADCMRepoI)),
        default_adcm_url=conf.default_adcm_url,
        status_base_path=conf.status_service_base_path,
    )

    if not resolved_url:
        message = (
            "Could not resolve external status service url: "
            "no Consul discovery result and DEFAULT_ADCM_URL is not set. "
            "The worker cannot report status events without it, refusing to start."
        )
        raise StatusServiceUrlResolutionError(message)

    status_service_url.set_external(resolved_url)
    logger.info("Worker status events will be sent to %s", resolved_url)


def install() -> None:
    # dispatch deduplicates receivers, so repeated installation is harmless;
    # connecting on the producer side is inert — worker_init never fires there
    worker_init.connect(setup_status_service_url)


def _discover_status_service_url(*, backend: ConsulBackend, adcm_uuid: str | None) -> str | None:
    try:
        entries = backend.discover(ADCM_SERVICE_NAME, tag=adcm_uuid)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to discover ADCM in Consul")
        return None

    return extract_status_service_url(entries)
