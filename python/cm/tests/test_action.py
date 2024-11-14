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

from configparser import ConfigParser
from pathlib import Path
import json

from adcm.tests.base import BaseTestCase, BusinessLogicMixin
from core.job.runners import ADCMSettings, AnsibleSettings, ExternalSettings, IntegrationsSettings
from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_409_CONFLICT

from cm.api import add_service_to_cluster
from cm.models import Action, Component, MaintenanceMode, Prototype
from cm.services.job.run._target_factories import prepare_ansible_environment
from cm.services.job.run.repo import JobRepoImpl
from cm.tests.utils import (
    gen_action,
    gen_bundle,
    gen_cluster,
    gen_host,
    gen_prototype,
    gen_provider,
)

plausible_action_variants = {
    "unlimited": {
        "state_available": "any",
        "state_unavailable": [],
        "multi_state_available": "any",
        "multi_state_unavailable": [],
    },
    "limited_by_available_state": {
        "state_available": ["bimbo"],
        "state_unavailable": [],
        "multi_state_available": "any",
        "multi_state_unavailable": [],
    },
    "limited_by_unavailable_state": {
        "state_available": "any",
        "state_unavailable": ["bimbo"],
        "multi_state_available": "any",
        "multi_state_unavailable": [],
    },
    "limited_by_available_multi_state": {
        "state_available": "any",
        "state_unavailable": [],
        "multi_state_available": ["bimbo"],
        "multi_state_unavailable": [],
    },
    "limited_by_unavailable_multi_state": {
        "state_available": "any",
        "state_unavailable": [],
        "multi_state_available": "any",
        "multi_state_unavailable": ["bimbo"],
    },
    "limited_by_available": {
        "state_available": ["bimbo"],
        "state_unavailable": [],
        "multi_state_available": ["bimbo"],
        "multi_state_unavailable": [],
    },
    "limited_by_unavailable": {
        "state_available": "any",
        "state_unavailable": ["bimbo"],
        "multi_state_available": "any",
        "multi_state_unavailable": ["bimbo"],
    },
    "hidden_by_unavailable_state": {
        "state_available": "any",
        "state_unavailable": "any",
        "multi_state_available": "any",
        "multi_state_unavailable": [],
    },
    "hidden_by_unavailable_multi_state": {
        "state_available": "any",
        "state_unavailable": [],
        "multi_state_available": "any",
        "multi_state_unavailable": "any",
    },
}
cluster_variants = {
    "unknown-unknown": {"state": "unknown", "_multi_state": ["unknown"]},
    "bimbo-unknown": {"state": "bimbo", "_multi_state": ["unknown"]},
    "unknown-bimbo": {"state": "unknown", "_multi_state": ["bimbo"]},
    "bimbo-bimbo": {"state": "bimbo", "_multi_state": ["bimbo"]},
}
expected_results = {
    "unknown-unknown": {
        "unlimited": True,
        "limited_by_available_state": False,
        "limited_by_unavailable_state": True,
        "limited_by_available_multi_state": False,
        "limited_by_unavailable_multi_state": True,
        "limited_by_available": False,
        "limited_by_unavailable": True,
        "hidden_by_unavailable_state": False,
        "hidden_by_unavailable_multi_state": False,
    },
    "bimbo-unknown": {
        "unlimited": True,
        "limited_by_available_state": True,
        "limited_by_unavailable_state": False,
        "limited_by_available_multi_state": False,
        "limited_by_unavailable_multi_state": True,
        "limited_by_available": False,
        "limited_by_unavailable": False,
        "hidden_by_unavailable_state": False,
        "hidden_by_unavailable_multi_state": False,
    },
    "unknown-bimbo": {
        "unlimited": True,
        "limited_by_available_state": False,
        "limited_by_unavailable_state": True,
        "limited_by_available_multi_state": True,
        "limited_by_unavailable_multi_state": False,
        "limited_by_available": False,
        "limited_by_unavailable": False,
        "hidden_by_unavailable_state": False,
        "hidden_by_unavailable_multi_state": False,
    },
    "bimbo-bimbo": {
        "unlimited": True,
        "limited_by_available_state": True,
        "limited_by_unavailable_state": False,
        "limited_by_available_multi_state": True,
        "limited_by_unavailable_multi_state": False,
        "limited_by_available": True,
        "limited_by_unavailable": False,
        "hidden_by_unavailable_state": False,
        "hidden_by_unavailable_multi_state": False,
    },
}


class ActionAllowTest(BusinessLogicMixin, BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.test_files_dir = self.base_dir / "python" / "cm" / "tests" / "files"

        _, self.cluster, _ = self.upload_bundle_create_cluster_config_log(
            bundle_path=Path(self.test_files_dir, "cluster_test_host_actions_mm.tar"), cluster_name="test-cluster-1"
        )
        add_service_to_cluster(
            cluster=self.cluster,
            proto=Prototype.objects.get(name="service_1", display_name="Service 1", type="service"),
        )

        provider = gen_provider()
        self.host_1 = gen_host(provider=provider, cluster=self.cluster, fqdn="test-host-1")
        self.host_2 = gen_host(provider=provider, cluster=self.cluster, fqdn="test-host-2")
        self.host_3 = gen_host(provider=provider, cluster=self.cluster, fqdn="test-host-3")

        component_1 = Component.objects.get(
            cluster=self.cluster, prototype__name="component_1", prototype__display_name="Component 1 from Service 1"
        )
        component_2 = Component.objects.get(
            cluster=self.cluster, prototype__name="component_2", prototype__display_name="Component 2 from Service 1"
        )

        self.set_hostcomponent(
            cluster=self.cluster,
            entries=[
                (self.host_1, component_1),
                (self.host_2, component_1),
                (self.host_2, component_2),
                (self.host_3, component_2),
            ],
        )

        self.host_action_comp1_allowed_in_mm = Action.objects.get(
            prototype=component_1.prototype, name="s1_c1_action_allowed_in_mm", allow_in_maintenance_mode=True
        )
        self.host_action_comp1_disallowed_in_mm = Action.objects.get(
            prototype=component_1.prototype, name="s1_c1_action_disallowed_in_mm", allow_in_maintenance_mode=False
        )
        self.host_action_comp2_allowed_in_mm = Action.objects.get(
            prototype=component_2.prototype, name="s1_c2_action_allowed_in_mm", allow_in_maintenance_mode=True
        )
        self.host_action_comp2_disallowed_in_mm = Action.objects.get(
            prototype=component_2.prototype, name="s1_c2_action_disallowed_in_mm", allow_in_maintenance_mode=False
        )

        _, self.cluster_2, _ = self.upload_bundle_create_cluster_config_log(
            bundle_path=Path(self.test_files_dir, "cluster_with_various_actions.tar"), cluster_name="test-cluster-2"
        )
        self.service_2_robot = add_service_to_cluster(
            cluster=self.cluster_2,
            proto=Prototype.objects.get(name="robot", type="service"),
        )
        self.component_wheel_of_robot = Component.objects.get(cluster=self.cluster_2, prototype__name="wheel")

    def test_variants(self):
        bundle = gen_bundle()
        prototype = gen_prototype(bundle, "cluster")
        cluster = gen_cluster(bundle=bundle, prototype=prototype)
        action = gen_action(bundle=bundle, prototype=prototype)

        for state_name, cluster_states in cluster_variants.items():
            for cl_attr, cl_value in cluster_states.items():
                setattr(cluster, cl_attr, cl_value)
            cluster.save()

            for req_name, req_states in plausible_action_variants.items():
                for act_attr, act_value in req_states.items():
                    setattr(action, act_attr, act_value)
                action.save()

                self.assertIs(action.allowed(cluster), expected_results[state_name][req_name])

    def test_run_host_actions_allowed_on_host_in_mm_success(self):
        self.host_1.maintenance_mode = MaintenanceMode.ON
        self.host_1.save()

        response: Response = self.client.post(
            path=reverse(
                viewname="v1:run-task",
                kwargs={
                    "cluster_id": self.cluster.pk,
                    "host_id": self.host_1.pk,
                    "object_type": "host",
                    "action_id": self.host_action_comp1_allowed_in_mm.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.host_2.maintenance_mode = MaintenanceMode.ON
        self.host_2.save()

        response: Response = self.client.post(
            path=reverse(
                viewname="v1:run-task",
                kwargs={
                    "cluster_id": self.cluster.pk,
                    "host_id": self.host_2.pk,
                    "object_type": "host",
                    "action_id": self.host_action_comp2_allowed_in_mm.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_run_host_actions_disallowed_on_host_in_mm_fail(self):
        self.host_1.maintenance_mode = MaintenanceMode.ON
        self.host_1.save()

        response: Response = self.client.post(
            path=reverse(
                viewname="v1:run-task",
                kwargs={
                    "cluster_id": self.cluster.pk,
                    "host_id": self.host_1.pk,
                    "object_type": "host",
                    "action_id": self.host_action_comp1_disallowed_in_mm.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        self.host_3.maintenance_mode = MaintenanceMode.ON
        self.host_3.save()

        response: Response = self.client.post(
            path=reverse(
                viewname="v1:run-task",
                kwargs={
                    "cluster_id": self.cluster.pk,
                    "host_id": self.host_3.pk,
                    "object_type": "host",
                    "action_id": self.host_action_comp2_disallowed_in_mm.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_host_in_mm_does_not_affect_other_host_actions_success(self):
        self.host_2.maintenance_mode = MaintenanceMode.ON
        self.host_2.save()

        response: Response = self.client.post(
            path=reverse(
                viewname="v1:run-task",
                kwargs={
                    "cluster_id": self.cluster.pk,
                    "host_id": self.host_1.pk,
                    "object_type": "host",
                    "action_id": self.host_action_comp1_disallowed_in_mm.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse(
                viewname="v1:run-task",
                kwargs={
                    "cluster_id": self.cluster.pk,
                    "host_id": self.host_3.pk,
                    "object_type": "host",
                    "action_id": self.host_action_comp2_disallowed_in_mm.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_component_mm_affects_service_actions_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v1:object-action",
                kwargs={
                    "cluster_id": self.cluster_2.pk,
                    "service_id": self.service_2_robot.pk,
                    "object_type": "service",
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(all(action["start_impossible_reason"] is None for action in response.json()))

        self.component_wheel_of_robot.maintenance_mode = MaintenanceMode.ON
        self.component_wheel_of_robot.save()

        response: Response = self.client.get(
            path=reverse(
                viewname="v1:object-action",
                kwargs={
                    "cluster_id": self.cluster_2.pk,
                    "service_id": self.service_2_robot.pk,
                    "object_type": "service",
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        disallowed_in_mm_action = [
            action for action in response.json() if action["name"] == "regular_action_disallowed"
        ][0]
        self.assertIsNotNone(disallowed_in_mm_action["start_impossible_reason"])

    def test_component_mm_affects_cluster_actions_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v1:object-action",
                kwargs={
                    "cluster_id": self.cluster_2.pk,
                    "object_type": "cluster",
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(all(action["start_impossible_reason"] is None for action in response.json()))

        self.component_wheel_of_robot.maintenance_mode = MaintenanceMode.ON
        self.component_wheel_of_robot.save()

        response: Response = self.client.get(
            path=reverse(
                viewname="v1:object-action",
                kwargs={
                    "cluster_id": self.cluster_2.pk,
                    "object_type": "cluster",
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIsNotNone(
            [action for action in response.json() if action["name"] == "regular_action_disallowed"][0][
                "start_impossible_reason"
            ]
        )

    def test_service_mm_affects_cluster_actions_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v1:object-action",
                kwargs={
                    "cluster_id": self.cluster_2.pk,
                    "object_type": "cluster",
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(all(action["start_impossible_reason"] is None for action in response.json()))

        self.service_2_robot.maintenance_mode = MaintenanceMode.ON
        self.service_2_robot.save()

        response: Response = self.client.get(
            path=reverse(
                viewname="v1:object-action",
                kwargs={
                    "cluster_id": self.cluster_2.pk,
                    "object_type": "cluster",
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIsNotNone(
            [action for action in response.json() if action["name"] == "regular_action_disallowed"][0][
                "start_impossible_reason"
            ]
        )


class TestActionParams(BaseTestCase, BusinessLogicMixin):
    def setUp(self) -> None:
        super().setUp()

        bundle = self.add_bundle(
            source_dir=self.base_dir / "python" / "cm" / "tests" / "bundles" / "cluster_with_action_params"
        )

        self.cluster = self.create_cluster(bundle_pk=bundle.pk, name="test_cluster_with_action_params")
        self.service = self.add_services_to_cluster(["same_actioned_service"], cluster=self.cluster).get()
        self.component = self.service.components.get()

        self.action_full = Action.objects.get(prototype=self.cluster.prototype, name="action_full")
        self.action_jinja_2_native_false = Action.objects.get(
            prototype=self.cluster.prototype, name="action_jinja2Native_false"
        )
        self.action_jinja_2_native_absent = Action.objects.get(
            prototype=self.cluster.prototype, name="action_jinja2Native_absent"
        )
        self.action_ansible_tags_absent = Action.objects.get(
            prototype=self.component.prototype, name="action_ansibleTags_absent"
        )
        self.action_custom_fields_absent = Action.objects.get(
            prototype=self.service.prototype, name="action_customFields_absent"
        )

        self.configuration = ExternalSettings(
            adcm=ADCMSettings(code_root_dir=settings.CODE_DIR, run_dir=settings.RUN_DIR, log_dir=settings.LOG_DIR),
            ansible=AnsibleSettings(ansible_secret_script=settings.CODE_DIR / "ansible_secret.py"),
            integrations=IntegrationsSettings(status_server_token=settings.STATUS_SECRET_KEY),
        )

        self.default_expected_ansible_cfg = {
            "defaults": (
                ("stdout_callback", "yaml"),
                ("deprecation_warnings", "False"),
                ("callback_whitelist", "profile_tasks"),
                ("forks", "5"),
            ),
            "ssh_connection": (("retries", "3"), ("pipelining", "True")),
        }

    def _generate_and_read_target_files(self, action_pk: int, alternative_path: str = "") -> tuple[ConfigParser, dict]:
        response = self.client.post(
            path=alternative_path
            or reverse(
                viewname="v2:cluster-action-run",
                kwargs={
                    "cluster_pk": self.cluster.pk,
                    "pk": action_pk,
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        task = JobRepoImpl.get_task(id=response.json()["id"])
        job, *_ = JobRepoImpl.get_task_jobs(task_id=task.id)

        job_dir: Path = self.directories["RUN_DIR"] / str(job.id)
        job_dir.mkdir(parents=True)
        prepare_ansible_environment(task=task, job=job, configuration=self.configuration)

        ansible_cfg_file: Path = job_dir / "ansible.cfg"
        config_json_file: Path = job_dir / "config.json"

        if not ansible_cfg_file.is_file() or not config_json_file.is_file():
            raise ValueError("Not all files exist")

        config_parser = ConfigParser()
        config_parser.read(ansible_cfg_file.absolute())

        return config_parser, json.loads(config_json_file.read_text(encoding="utf-8"))

    def test_params_full(self):
        expected_job_params = {
            "ansible_tags": "ansible_tag1, ansible_tag2",
            "custom_list": [1, "two", 3.0],
            "custom_map": {"1": "two", "five": 6, "three": 4.0},
            "custom_str": "custom_str_value",
            "jinja2_native": True,
        }

        ansible_cfg_content, config_json_content = self._generate_and_read_target_files(action_pk=self.action_full.pk)

        self.assertListEqual(ansible_cfg_content.sections(), list(self.default_expected_ansible_cfg.keys()))
        self.assertSetEqual(
            set(ansible_cfg_content.items("defaults")), set(self.default_expected_ansible_cfg["defaults"])
        )
        self.assertDictEqual(config_json_content["job"]["params"], expected_job_params)

    def test_params_jinja_2_native_false(self):
        expected_job_params = {
            "ansible_tags": "ansible_tag1, ansible_tag2",
            "custom_list": [1, "two", 3.0],
            "custom_map": {"1": "two", "five": 6, "three": 4.0},
            "custom_str": "custom_str_value",
            "jinja2_native": False,
        }

        ansible_cfg_content, config_json_content = self._generate_and_read_target_files(
            action_pk=self.action_jinja_2_native_false.pk
        )

        self.assertListEqual(ansible_cfg_content.sections(), list(self.default_expected_ansible_cfg.keys()))
        self.assertSetEqual(
            set(ansible_cfg_content.items("defaults")), set(self.default_expected_ansible_cfg["defaults"])
        )
        self.assertDictEqual(config_json_content["job"]["params"], expected_job_params)

    def test_params_jinja_2_native_absent(self):
        expected_job_params = {
            "ansible_tags": "ansible_tag1, ansible_tag2",
            "custom_list": [1, "two", 3.0],
            "custom_map": {"1": "two", "five": 6, "three": 4.0},
            "custom_str": "custom_str_value",
        }

        ansible_cfg_content, config_json_content = self._generate_and_read_target_files(
            action_pk=self.action_jinja_2_native_absent.pk
        )

        self.assertListEqual(ansible_cfg_content.sections(), list(self.default_expected_ansible_cfg.keys()))
        self.assertSetEqual(
            set(ansible_cfg_content.items("defaults")), set(self.default_expected_ansible_cfg["defaults"])
        )
        self.assertDictEqual(config_json_content["job"]["params"], expected_job_params)

    def test_params_ansible_tags_absent(self):
        expected_job_params = {
            "custom_list": [1, "two", 3.0],
            "custom_map": {"1": "two", "five": 6, "three": 4.0},
            "custom_str": "custom_str_value",
            "jinja2_native": True,
        }

        ansible_cfg_content, config_json_content = self._generate_and_read_target_files(
            action_pk=self.action_ansible_tags_absent.pk,
            alternative_path=reverse(
                viewname="v2:component-action-run",
                kwargs={
                    "cluster_pk": self.cluster.pk,
                    "service_pk": self.service.pk,
                    "component_pk": self.component.pk,
                    "pk": self.action_ansible_tags_absent.pk,
                },
            ),
        )

        self.assertListEqual(ansible_cfg_content.sections(), list(self.default_expected_ansible_cfg.keys()))
        self.assertSetEqual(
            set(ansible_cfg_content.items("defaults")), set(self.default_expected_ansible_cfg["defaults"])
        )
        self.assertDictEqual(config_json_content["job"]["params"], expected_job_params)

    def test_params_custom_fields_absent(self):
        expected_job_params = {"ansible_tags": "ansible_tag1, ansible_tag2", "jinja2_native": True}

        ansible_cfg_content, config_json_content = self._generate_and_read_target_files(
            action_pk=self.action_custom_fields_absent.pk,
            alternative_path=reverse(
                viewname="v2:service-action-run",
                kwargs={
                    "cluster_pk": self.cluster.pk,
                    "service_pk": self.service.pk,
                    "pk": self.action_custom_fields_absent.pk,
                },
            ),
        )

        self.assertListEqual(ansible_cfg_content.sections(), list(self.default_expected_ansible_cfg.keys()))
        self.assertSetEqual(
            set(ansible_cfg_content.items("defaults")), set(self.default_expected_ansible_cfg["defaults"])
        )
        self.assertDictEqual(config_json_content["job"]["params"], expected_job_params)
