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

from unittest import TestCase

from core.action.types import JobSpecV1

from cm.impl.common.execution_plan import (
    STORED_VERSION,
    UnsupportedExecutionPlanError,
    dump_execution_plan,
    parse_execution_plan,
)
from cm.tests.scripts import build_script_spec


class TestExecutionPlanStorage(TestCase):
    def setUp(self) -> None:
        self.spec = JobSpecV1.from_scripts(build_script_spec("/0", "first"), build_script_spec("/1", "second"))

    def test_roundtrip_success(self):
        self.assertEqual(parse_execution_plan(dump_execution_plan(self.spec)), self.spec)

    def test_version_is_stored_aside_from_the_spec(self):
        stored = dump_execution_plan(self.spec)

        self.assertEqual(stored["version"], STORED_VERSION)
        # the spec itself knows nothing about the envelope
        self.assertNotIn("version", JobSpecV1.model_fields)

    def test_unknown_version_fail(self):
        for case, stored in (
            ("newer", dump_execution_plan(self.spec) | {"version": STORED_VERSION + 1}),
            ("absent", self.spec.model_dump(mode="json")),
        ):
            with self.subTest(case), self.assertRaises(UnsupportedExecutionPlanError):
                parse_execution_plan(stored)
