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

from core.bundle import BundleContext
from core.dynamic_bundle.render import BundleRenderer
from core.templates import parse_template
from tests.base import BaseTestCase
from tests.deprecated import BusinessLogicMixin
from use_cases.dto import ConfigurationDTO, RunActionDTO
import core

from cm.legacy.services.bundle_alt.render import ActionArgs, TaskArgs
from cm.models import Action, JobLog, TaskLog
from cm.tests.dependencies import WithDishkaContainer
from cm.tests.test_action_host_group import ScheduleTask


class TestActionProcessContext(WithDishkaContainer, BusinessLogicMixin, BaseTestCase):
    maxDiff = None

    def setUp(self) -> None:
        super().setUp()

        bundle_dir = Path(__file__).parent / "bundles" / "cluster_template"

        bundle = self.add_bundle(bundle_dir)

        self.cluster = self.uc.add_cluster(bundle=bundle, name="cc")

    def test_render_templates_in_regular_action(self):
        action = Action.objects.get(prototype_id=self.cluster.prototype_id, name="with_templates")
        input_config = {"config": {"field": "something"}, "attr": {}}

        configuration = ConfigurationDTO(
            convert=lambda x, _: x,
            input_config=core.config.Configuration(values=input_config["config"], attributes=input_config["attr"]),
        )
        with self.container() as container:
            container.get(ScheduleTask).do(
                action_orm=action, target=self.cluster, payload=RunActionDTO(configuration=configuration)
            )

        task_id = self.task_runner.expect_task_launched().id

        jobs = JobLog.objects.filter(task_id=task_id)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].name, "first")
        config = TaskLog.objects.values_list("config", flat=True).get(id=task_id)
        self.assertEqual(config, input_config["config"])


class TestTemplateRendering(WithDishkaContainer, BusinessLogicMixin, BaseTestCase):
    def test_adcm_7609(self):
        bundle_path = Path(__file__).parent / "bundles" / "adcm_7609"
        bundle = self.uc.upload_bundle(bundle_path)
        cluster = self.uc.add_cluster(bundle=bundle, name="aa")
        action = Action.objects.get(name="aa", prototype_id=cluster.prototype_id)

        template = parse_template(action.scripts_template)
        args = TaskArgs(target_object=cluster, owner_object=cluster, action=action)
        context = BundleContext(
            id=bundle.pk,
            # we'll use static path for this case
            root=bundle_path,
            contract_version="2.1",
        )

        with self.container() as container:
            renderer = container.get(BundleRenderer[ActionArgs, TaskArgs])
            scripts = renderer.render_scripts_for_action(
                template=template, args=args, bundle_context=context, action_allow_to_terminate=False
            )

        self.assertEqual(len(scripts), 1)
        self.assertEqual(scripts[0].script, "wizard_jinja/scripts/sleep.yaml")
