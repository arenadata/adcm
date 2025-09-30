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

from adcm.tests.base import BaseTestCase, BusinessLogicMixin

from cm.models import Action, JobLog
from cm.services.job.action import ActionRunPayload, run_action
from cm.tests.mocks.task_runner import RunTaskMock


class TestActionProcessContext(BusinessLogicMixin, BaseTestCase):
    maxDiff = None

    def setUp(self) -> None:
        super().setUp()

        bundle_dir = Path(__file__).parent / "bundles" / "cluster_template"

        bundle = self.add_bundle(bundle_dir)

        self.cluster = self.add_cluster(bundle=bundle, name="cc")

    def test_render_templates_in_regular_action(self):
        action = Action.objects.get(prototype_id=self.cluster.prototype_id, name="with_templates")
        input_config = {"config": {"field": "something"}, "attr": {}}

        with RunTaskMock() as task_mock:
            run_action(
                action=action,
                obj=self.cluster,
                payload=ActionRunPayload(conf=input_config["config"], attr=input_config["attr"]),
            )

        self.assertIsNotNone(task_mock.target_task)
        jobs = JobLog.objects.filter(task_id=task_mock.target_task.pk)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].name, "first")
        config = task_mock.target_task.config
        self.assertEqual(config, input_config["config"])
