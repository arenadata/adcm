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

from dataclasses import dataclass
from typing import Any
import logging

from core.adcm import ADCMRepoI
from core.result import Fail, Success

from integrations.celery.helpers import read_adcm_uuid
from integrations.consul import ConsulBackend, url_with_base_path

logger = logging.getLogger("worker.celery")

ADCM_SERVICE_NAME = "adcm"
STATUS_SERVICE_URL_META = "status_service_url"


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


@dataclass(slots=True)
class ResolveExternalStatusServiceURL:
    """
    Resolve the externally-reachable status service URL for worker -> status reporting.
    """

    repo: ADCMRepoI
    consul_backend: ConsulBackend | None
    default_adcm_url: str | None
    status_base_path: str

    def resolve(self) -> Success[str] | Fail[str]:
        if self.consul_backend is None and not self.default_adcm_url:
            return Fail("neither CONSUL_URL nor DEFAULT_ADCM_URL is set, at least one of them is mandatory")

        if self.consul_backend is not None:
            adcm_uuid = read_adcm_uuid(self.repo)
            try:
                entries = self.consul_backend.discover(ADCM_SERVICE_NAME, tag=adcm_uuid)
                url = extract_status_service_url(entries)
                if url:
                    return Success(url)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to discover ADCM in Consul")

        if self.default_adcm_url:
            # consul-less fallback: same formula the backend uses to build the URL
            # it advertises in Consul meta (see application.startup.consul); when
            # discovery works, the advertised URL above wins - it is authoritative
            # for scheme and base path
            return Success(url_with_base_path(self.default_adcm_url, self.status_base_path))

        return Fail("no Consul discovery result and DEFAULT_ADCM_URL is not set")
