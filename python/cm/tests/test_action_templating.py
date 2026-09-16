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
from unittest_parametrize import ParametrizedTestCase, parametrize
from use_cases.dto import ConfigurationDTO, RunActionDTO
from use_cases.transition.job.schedule import RetrieveConfigurationForAction
import core

from cm.impl.bundle.context import ActionArgs, TaskArgs
from cm.models import Action, JobLog, TaskLog
from cm.tests.dependencies import WithDishkaContainer
from cm.tests.test_action_host_group import ScheduleTask


class TestActionProcessContext(ParametrizedTestCase, WithDishkaContainer, BusinessLogicMixin, BaseTestCase):
    maxDiff = None

    def setUp(self) -> None:
        super().setUp()

        self.bundle_dir = Path(__file__).parent / "bundles" / "cluster_template"

        bundle = self.add_bundle(self.bundle_dir)

        self.cluster = self.uc.add_cluster(bundle=bundle, name="cc")

    def test_render_templates_in_regular_action(self):
        action = Action.objects.get(prototype_id=self.cluster.prototype_id, name="with_templates")
        input_config = {"config": {"field": "something"}, "attr": {}}

        configuration = ConfigurationDTO(
            convert=lambda x, _: x,
            input_config=core.config.Configuration(values=input_config["config"], attributes=input_config["attr"]),
        )
        with self.container() as container:
            launched_task = container.get(ScheduleTask).do(
                action_orm=action, target=self.cluster, payload=RunActionDTO(configuration=configuration)
            )

        task_id = launched_task.pk

        jobs = JobLog.objects.filter(task_id=task_id)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].name, "first")
        config = TaskLog.objects.values_list("config", flat=True).get(id=task_id)
        self.assertEqual(config, input_config["config"])

    def test_adcm_5556_paths_in_rendered_config_are_resolved(self):
        expected_full_yspec = {
            "root": {
                "match": "dict",
                "items": {"string": "string", "integer": "integer"},
            },
            "string": {"match": "string"},
            "integer": {"match": "int"},
        }
        expected_relative_yspec = {
            **expected_full_yspec,
            "root": {**expected_full_yspec["root"], "items": {"tutu": "string", "tata": "integer"}},
        }
        action = Action.objects.get(prototype_id=self.cluster.prototype_id, name="adcm_5556_paths")

        with self.container() as container:
            result = container.get(RetrieveConfigurationForAction).do(action_orm=action, target=self.cluster)
            secrets = container.get(core.config.secrets.AnsibleSecrets)

        self.assertIsNotNone(result)
        specification, defaults, _, _ = result
        self.assertDictEqual(specification.parameters["/full"].yspec, expected_full_yspec)
        self.assertDictEqual(specification.parameters["/relative"].yspec, expected_relative_yspec)
        self.assertEqual(defaults.values["/fplain"], (self.bundle_dir / "outer" / "text.yaml").read_text())
        self.assertEqual(
            secrets.decrypt(defaults.values["/fsec"]),
            (self.bundle_dir / "outer" / "configs" / "text.yaml").read_text(),
        )

    @parametrize(
        ("is_active", "expected_jobs"),
        [(False, ["default", "inactive"]), (True, ["default", "active"])],
        ids=["inactive", "active"],
    )
    def test_use_activatable_group_in_config(self, is_active: bool, expected_jobs: list[str]):
        # related with ADCM-6012
        action = Action.objects.get(prototype_id=self.cluster.prototype_id, name="with_activatable_group")

        configuration = ConfigurationDTO(
            convert=lambda value, _: value,
            input_config=core.config.Configuration(
                values={"group": {"x": 2}},
                attributes={"/group": core.config.Attributes(is_active=is_active)},
            ),
        )

        with self.container() as container:
            task = container.get(ScheduleTask).do(
                action_orm=action,
                target=self.cluster,
                payload=RunActionDTO(configuration=configuration),
            )

        self.assertListEqual(
            list(JobLog.objects.filter(task=task).order_by("id").values_list("name", flat=True)),
            expected_jobs,
        )


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

        self.assertEqual(list(scripts.scripts), ["/0"])
        self.assertEqual(scripts.scripts["/0"].script.path, "wizard_jinja/scripts/sleep.yaml")
