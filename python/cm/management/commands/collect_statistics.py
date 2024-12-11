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

from logging import getLogger
from typing import NamedTuple
from urllib.parse import urlunparse
import os
import shutil
import socket

from audit.alt.background import audit_background_operation
from audit.models import AuditLogOperationType
from django.conf import settings
from django.core.management import BaseCommand
from django.db.models import Q
from django.utils import timezone

from cm.adcm_config.config import get_adcm_config
from cm.collect_statistics.collectors import ADCMEntities, BundleCollector, RBACCollector
from cm.collect_statistics.encoders import TarFileEncoder
from cm.collect_statistics.senders import SenderSettings, StatisticSender
from cm.collect_statistics.storages import JSONFile, TarFileWithJSONFileStorage
from cm.models import ADCM

SENDER_REQUEST_TIMEOUT = 15.0
DATE_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
STATISTIC_DIR = settings.TMP_DIR / "statistics"
STATISTIC_DIR.mkdir(exist_ok=True)

logger = getLogger("background_tasks")

collect_not_enterprise = BundleCollector(date_format=DATE_TIME_FORMAT, filters=[~Q(edition="enterprise")])
collect_all = BundleCollector(date_format=DATE_TIME_FORMAT, filters=[])


class URLComponents(NamedTuple):
    scheme: str
    netloc: str
    path: str
    params: str = ""
    query: str = ""
    fragment: str = ""


def is_internal() -> bool:
    try:
        with socket.create_connection(("adsw.io", 80), timeout=1):
            return True
    except TimeoutError:
        logger.exception(msg="Timeout error")
        return False
    except socket.gaierror:
        logger.exception(msg="Address-related error")
        return False


def get_statistics_url() -> str:
    scheme = "http"
    url_path = "/api/v1/statistic/adcm"

    if (netloc := os.getenv("STATISTICS_URL")) is None:
        _, config = get_adcm_config(section="statistics_collection")
        netloc = config["url"]

    if len(splitted := netloc.split("://")) == 2:
        scheme = splitted[0]
        netloc = splitted[1]

    return urlunparse(components=URLComponents(scheme=scheme, netloc=netloc, path=url_path))


def get_enabled() -> bool:
    if os.getenv("STATISTICS_ENABLED") is not None:
        return os.environ["STATISTICS_ENABLED"].upper() in {"1", "TRUE"}

    attr, _ = get_adcm_config(section="statistics_collection")
    return bool(attr["active"])


class Command(BaseCommand):
    help = "Collect data and send to Statistic Server"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument(
            "--mode",
            choices=["send", "archive-all"],
            help=(
                "'send' - collect archive with only community bundles and send to Statistic Server, "
                "'archive-all' - collect community and enterprise bundles to archive and return path to file"
            ),
            default="archive-all",
        )

    @audit_background_operation(name='"Statistics collection on schedule" job', type_=AuditLogOperationType.UPDATE)
    def handle(self, *_, mode: str, **__):
        logger.debug(msg="Statistics collector: started")
        statistics_data = {
            "adcm": {
                "uuid": str(ADCM.objects.values_list("uuid", flat=True).get()),
                "version": settings.ADCM_VERSION,
                "is_internal": is_internal(),
            },
            "format_version": 0.3,
        }
        logger.debug(msg="Statistics collector: RBAC data preparation")
        rbac_entries_data: dict = RBACCollector(date_format=DATE_TIME_FORMAT)().model_dump()
        storage = TarFileWithJSONFileStorage(date_format=DATE_FORMAT)

        match mode:
            case "send":
                logger.debug(msg="Statistics collector: 'send' mode is used")

                if not get_enabled():
                    logger.debug(msg="Statistics collector: disabled")
                    return

                logger.debug(
                    msg="Statistics collector: bundles data preparation, collect everything except 'enterprise' edition"
                )
                bundle_data: ADCMEntities = collect_not_enterprise()
                storage.add(
                    JSONFile(
                        filename=f"{timezone.now().strftime(DATE_FORMAT)}_statistics.json",
                        data={**statistics_data, "data": {**rbac_entries_data, **bundle_data.model_dump()}},
                    )
                )
                logger.debug(msg="Statistics collector: archive preparation")
                archive = storage.gather()
                sender_settings = SenderSettings(
                    url=get_statistics_url(),
                    adcm_uuid=statistics_data["adcm"]["uuid"],
                    retries_limit=int(os.getenv("STATISTICS_RETRIES", 10)),
                    retries_frequency=int(os.getenv("STATISTICS_FREQUENCY", 1 * 60 * 60)),  # in seconds
                    request_timeout=SENDER_REQUEST_TIMEOUT,
                )
                logger.debug(msg="Statistics collector: sender preparation")
                sender = StatisticSender(settings=sender_settings)
                logger.debug(msg="Statistics collector: statistics sending has started")
                sender.send([archive])
                logger.debug(msg="Statistics collector: sending statistics completed")

            case "archive-all":
                logger.debug(msg="Statistics collector: 'archive-all' mode is used")
                logger.debug(msg="Statistics collector: bundles data preparation, collect everything")
                bundle_data: ADCMEntities = collect_all()
                storage.add(
                    JSONFile(
                        filename=f"{timezone.now().strftime(DATE_FORMAT)}_statistics.json",
                        data={**statistics_data, "data": {**rbac_entries_data, **bundle_data.model_dump()}},
                    )
                )
                logger.debug(msg="Statistics collector: archive preparation")
                archive = storage.gather()

                logger.debug(msg="Statistics collector: archive encoding")
                encoder = TarFileEncoder(suffix=".enc")
                encoded_file = encoder.encode(path_file=archive)
                # We use shutil here instead of Path.rename,
                # because of possible cross-device link problem (e.g. -v /adcm/data):
                # `OSError: [Errno 18] Cross-device link:`
                encoded_file = shutil.move(str(encoded_file), str(STATISTIC_DIR / encoded_file.name))

                self.stdout.write(f"Data saved in: {encoded_file}")
            case _:
                pass

        logger.debug(msg="Statistics collector: finished")
