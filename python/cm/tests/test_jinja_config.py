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

from pathlib import Path
from unittest.mock import patch
import unittest

from adcm.tests.base import BaseTestCase, BusinessLogicMixin, TaskTestMixin

from cm.models import Action
from cm.services.config.jinja import get_jinja_config


class TestJinjaConfigBugs(BusinessLogicMixin, TaskTestMixin, BaseTestCase):
    maxDiff = None

    def setUp(self) -> None:
        super().setUp()

        self.bugs_bundle_dir = Path(__file__).parent / "bundles" / "bugs"

    def test_adcm_5556_incorrect_path_bug_old_processing(self):
        # ADCM-6746
        # with patch("cm.services.config.jinja.use_new_bundle_parsing_approach", return_value=False) as patched:
        self._test_adcm_5556_incorrect_path_bug()

        # patched.assert_called_once()

    @unittest.skip("ADCM-6747")
    def test_adcm_5556_incorrect_path_bug_new_processing(self):
        with patch("cm.services.config.jinja.use_new_bundle_parsing_approach", return_value=True) as patched:
            self._test_adcm_5556_incorrect_path_bug()

        patched.assert_called_once()

    def _test_adcm_5556_incorrect_path_bug(self) -> None:
        expected_full_limits = {
            "root": {
                "match": "dict_key_selection",
                "selector": "type",
                "variants": {"string": "string", "integer": "integer"},
            },
            "string": {"match": "string"},
            "integer": {"match": "int"},
        }
        expected_relative_limits = {
            **expected_full_limits,
            "root": {**expected_full_limits["root"], "variants": {"tutu": "string", "tata": "integer"}},
        }

        bundle = self.add_bundle(self.bugs_bundle_dir / "ADCM-5556")
        cluster = self.add_cluster(bundle=bundle, name="adcm-5556-cluster")
        action = Action.objects.get(prototype=cluster.prototype, name="with_j2_config")

        config_prototypes = {
            proto.name: {"limits": proto.limits, "default": str(proto.default)}
            for proto in get_jinja_config(cluster_relative_object=cluster, action=action)[0]
        }

        self.assertDictEqual(
            config_prototypes,
            {
                "full": {"limits": {"yspec": expected_full_limits}, "default": ""},
                "relative": {"limits": {"yspec": expected_relative_limits}, "default": ""},
                "fplain": {"limits": {}, "default": "outer/text.yaml"},
                "fsec": {"limits": {}, "default": "outer/configs/text.yaml"},
            },
        )
