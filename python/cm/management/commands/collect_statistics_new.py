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

import socket

from django.conf import settings
from django.core.management import BaseCommand

from cm.collect_statistics.collectors import (
    ADCMEntities,
    CommunityBundleCollector,
    EnterpriseBundleCollector,
    RBACCollector,
)
from cm.collect_statistics.encoders import TarFileEncoder
from cm.collect_statistics.senders import StatisticSender
from cm.collect_statistics.storages import JSONFile, TarFileWithJSONFileStorage, TarFileWithTarFileStorage
from cm.models import ADCM


def is_internal() -> bool:
    try:
        with socket.create_connection(("adsw.io", 80), timeout=1):
            return True
    except TimeoutError:
        return False


class Command(BaseCommand):
    help = "Collect data and send to Statistic Server"

    def add_arguments(self, parser):
        parser.add_argument("--full", action="store_true", help="collect all data")
        parser.add_argument("--send", action="store_true", help="send data to Statistic Server")
        parser.add_argument("--encode", action="store_true", help="encode data")

    def handle(self, *_, full: bool, send: bool, encode: bool, **__):
        date_format = "%Y-%m-%d %H:%M:%S"

        statistics_data = {
            "adcm": {
                "uuid": str(ADCM.objects.values_list("uuid", flat=True).get()),
                "version": settings.ADCM_VERSION,
                "is_internal": is_internal(),
            },
            "format_version": "0.2",
        }
        rbac_entries_data: dict = RBACCollector(date_format=date_format)().model_dump()

        community_bundle_data: ADCMEntities = CommunityBundleCollector(date_format=date_format)()
        community_storage = TarFileWithJSONFileStorage()

        community_storage.add(
            JSONFile(
                filename="community.json",
                data={**statistics_data, **rbac_entries_data, **community_bundle_data.model_dump()},
            )
        )
        community_archive = community_storage.gather()

        final_storage = TarFileWithTarFileStorage()
        final_storage.add(community_archive)

        if full:
            enterprise_bundle_data: ADCMEntities = EnterpriseBundleCollector(date_format=date_format)()
            enterprise_storage = TarFileWithJSONFileStorage()

            enterprise_storage.add(
                JSONFile(
                    filename="enterprise.json",
                    data={**statistics_data, **rbac_entries_data, **enterprise_bundle_data.model_dump()},
                )
            )
            final_storage.add(enterprise_storage.gather())

        final_archive = final_storage.gather()

        if encode:
            encoder = TarFileEncoder()
            encoder.encode(final_archive)

        if send:
            sender = StatisticSender()
            sender.send([community_archive])
