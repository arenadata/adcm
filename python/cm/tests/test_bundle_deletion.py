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

from adcm.tests.base import BaseTestCase
from cm.api import delete_host_provider
from cm.bundle import delete_bundle
from cm.errors import AdcmEx
from cm.tests.test_upgrade import (
    cook_cluster,
    cook_cluster_bundle,
    cook_provider,
    cook_provider_bundle,
)


class TestHC(BaseTestCase):
    def test_cluster_bundle_deletion(self):
        bundle = cook_cluster_bundle("1.0")
        cook_cluster(bundle, "TestCluster")
        try:
            delete_bundle(bundle)
        except AdcmEx as e:
            self.assertEqual(e.code, "BUNDLE_CONFLICT")
            self.assertEqual(e.msg, 'There is cluster #1 "TestCluster" of bundle #1 "ADH" 1.0')

    def test_provider_bundle_deletion(self):
        bundle = cook_provider_bundle("1.0")
        provider = cook_provider(bundle, "TestProvider")
        try:
            delete_bundle(bundle)
        except AdcmEx as e:
            self.assertEqual(e.code, "BUNDLE_CONFLICT")
            self.assertEqual(e.msg, 'There is provider #1 "TestProvider" of bundle #1 "DF" 1.0')

        try:
            delete_host_provider(provider)
        except AdcmEx as e:
            self.assertEqual(e.code, "PROVIDER_CONFLICT")
            self.assertEqual(
                e.msg, 'There is host #1 "server02.inter.net" of host provider #1 "TestProvider"'
            )
