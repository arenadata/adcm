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

from collections import defaultdict
from collections.abc import Collection, Sequence
from itertools import filterfalse
from operator import attrgetter
from pathlib import Path

from cm.models import ADCMEntity, ConfigLog, HostComponent
from django.db.models import Count
from init_db import init
from tests.integrations.concurrency.parallel import CallOutcome
from tests.suites import GenericTransactionTestCase

BUNDLES_DIR = Path(__file__).parent / "bundles"

HOST_FQDN_1 = "host-1"
HOST_FQDN_2 = "host-2"


class ConcurrencyBasicTestCase(GenericTransactionTestCase):
    maxDiff = None

    def setUp(self):
        init(container=self.container)

        cluster_bundle = self.uc.upload_bundle(BUNDLES_DIR / "cluster")
        provider_bundle = self.uc.upload_bundle(BUNDLES_DIR / "provider")

        self.cluster = self.uc.add_cluster(bundle=cluster_bundle, name="Concurrency cluster")

        self.provider = self.uc.add_provider(bundle=provider_bundle, name="Concurrency provider")
        self.host_1 = self.uc.add_host(provider=self.provider, fqdn=HOST_FQDN_1, cluster=self.cluster)
        self.host_2 = self.uc.add_host(provider=self.provider, fqdn=HOST_FQDN_2, cluster=self.cluster)

    def split_by_error(self, outcomes: Collection[CallOutcome]) -> tuple[list[CallOutcome], list[CallOutcome]]:
        error_field = attrgetter("error")
        return list(filterfalse(error_field, outcomes)), list(filter(error_field, outcomes))

    def assert_errors_in_outcomes(self, outcomes: Sequence[CallOutcome], errors: list[str]) -> None:
        """
        Check that substrings in `errors` are present given amount of times and all errors are accounted for
        """
        report = {"unaccounted": [], "substrings": defaultdict(lambda: {"expected": 0, "actual": 0})}
        for err in errors:
            report["substrings"][err]["expected"] += 1

        _, with_errors = self.split_by_error(outcomes)

        for outcome in with_errors:
            for substring, counts in report["substrings"].items():
                if substring in str(outcome.error):
                    counts["actual"] += 1
                    break
            else:
                report["unaccounted"].append(outcome)

        result = {
            "Error substrings without enough matches": {
                sub: f"{counts['actual']}/{counts['expected']}"
                for sub, counts in report["substrings"].items()
                if counts["actual"] != counts["expected"]
            },
            "Errors that wasn't expected": {
                "total": len(report["unaccounted"]),
                "details": [(i, str(out.error)) for i, out in enumerate(report["unaccounted"])],
            }
            if report["unaccounted"]
            else {},
        }

        self.assertDictEqual(result, {k: {} for k in result})

    def assert_mapping(self, expected: list[tuple[str, str, int]]) -> None:
        """
        Expected should have records with (service name, component name, hosts amount).
        Amount of hosts is asserted, because database has constraints on duplicates
        and it's difficult to determine which host will be mapped exactly.
        """
        actual = list(
            HostComponent.objects.filter(cluster_id=self.cluster.pk)
            .values_list(
                "service__prototype__name",
                "component__prototype__name",
            )
            .annotate(
                count=Count("host__fqdn"),
            )
            .order_by()
            .all()
        )
        self.assertCountEqual(actual, expected)

    def assert_config_count(self, target: ADCMEntity, expected: int) -> None:
        actual = ConfigLog.objects.filter(obj_ref=target.config).count()
        self.assertEqual(actual, expected)

    def assert_all_outcomes_synced_by_codepoint(self, outcomes: Sequence[CallOutcome]) -> None:
        self.assertTrue(all(o.synchronized and not o.serialized_by_lock for o in outcomes))

    def assert_all_outcomes_synced_by_lock(self, outcomes: Sequence[CallOutcome]) -> None:
        self.assertTrue(all(o.serialized_by_lock and not o.synchronized for o in outcomes))
