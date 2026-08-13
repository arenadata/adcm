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

import logging

from core.adcm import ADCMRepoI

logger = logging.getLogger("worker.celery.utils")


def read_adcm_uuid(repo: ADCMRepoI) -> str | None:
    """Read the ADCM uuid; best-effort (``None`` on failure)."""
    try:
        return repo.get_uuid()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to read ADCM uuid")
        return None
