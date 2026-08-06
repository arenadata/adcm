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
from unittest.mock import patch
from uuid import uuid4
import json

from core.action import (
    AssociatedProcess,
    CallingProcess,
    HcAclRule,
    JobParams,
    ServiceManageServiceEntry,
    TaskMappingDelta,
)
from core.cluster import ClusterService
from core.legacy.job.runners import (
    ADCMSettings,
    AnsibleSettings,
    ConsulSettings,
    ExternalSettings,
    IntegrationsSettings,
)
from core.types import ADCMCoreType
from django.conf import settings
from django.db.models import Model
from django.urls import reverse
from pydantic import ValidationError
from rbac.scenarios import RBACScenarios
from rest_framework.status import HTTP_200_OK
from tests.base import BaseTestCase
from tests.deprecated import TaskTestMixin
from tests.suites import ADCMDjangoAPISuite
from use_cases.transition.config import UpdateConfigurationFromJob
from use_cases.transition.service_manage import ManageClusterServices, _build_mapping_delta

from cm.converters import orm_object_to_core_type
from cm.errors import AdcmEx
from cm.impl.job.repo import JobRepo
from cm.legacy.api import add_service_to_cluster
from cm.legacy.services.job.run._target_factories import (
    internal_script_config_apply,
    internal_script_hc_apply,
    internal_script_service_manage,
    prepare_ansible_environment,
)
from cm.models import (
    Action,
    Component,
    ConfigLog,
    Host,
    HostComponent,
    MaintenanceMode,
    Prototype,
    Service,
    get_object_cluster,
)
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


class DummyObject:
    pass


class ActionAllowTest(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.test_files_dir = self.base_dir / "python" / "cm" / "tests" / "files"

        _, self.cluster, _ = self.upload_bundle_create_cluster_config_log(
            bundle_path=Path(self.test_files_dir, "cluster_test_host_actions_mm.tar"), cluster_name="test-cluster-1"
        )
        add_service_to_cluster(
            cluster=self.cluster,
            proto=Prototype.objects.get(name="service_1", display_name="Service 1", type="service"),
            rbac_scenarios=RBACScenarios(),
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

        self.uc.set_hostcomponent(
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
            rbac_scenarios=RBACScenarios(),
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


class TestActionParams(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        bundle = cls.uc.upload_bundle(
            src=cls.base_dir / "python" / "cm" / "tests" / "bundles" / "cluster_with_action_params"
        )

        cls.cluster = cls.uc.add_cluster(bundle=bundle, name="test_cluster_with_action_params")
        cls.service, *_ = cls.uc.add_services_to_cluster(["same_actioned_service"], cluster=cls.cluster)
        cls.component = cls.service.components.get()

        cls.action_full = Action.objects.get(prototype=cls.cluster.prototype, name="action_full")
        cls.action_jinja_2_native_false = Action.objects.get(
            prototype=cls.cluster.prototype, name="action_jinja2Native_false"
        )
        cls.action_jinja_2_native_absent = Action.objects.get(
            prototype=cls.cluster.prototype, name="action_jinja2Native_absent"
        )
        cls.action_ansible_tags_absent = Action.objects.get(
            prototype=cls.component.prototype, name="action_ansibleTags_absent"
        )
        cls.action_custom_fields_absent = Action.objects.get(
            prototype=cls.service.prototype, name="action_customFields_absent"
        )

        cls.configuration = ExternalSettings(
            adcm=ADCMSettings(code_root_dir=settings.CODE_DIR, run_dir=settings.RUN_DIR, log_dir=settings.LOG_DIR),
            ansible=AnsibleSettings(ansible_secret_script=settings.CODE_DIR / "ansible_secret.py"),
            integrations=IntegrationsSettings(status_server_token=settings.STATUS_SECRET_KEY),
            consul=ConsulSettings(
                url=settings.CONSUL_URL, datacenter=settings.CONSUL_DATACENTER, cacert_file=settings.CONSUL_CACERT_FILE
            ),
        )

        cls.default_expected_ansible_cfg = {
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

        task = JobRepo().get_task(id=response.json()["id"])
        job, *_ = JobRepo().get_task_jobs(task_id=task.id)

        job_dir: Path = self.directories.run / str(job.id)
        job_dir.mkdir(parents=True)
        prepare_ansible_environment(
            task=task, job=job, configuration=self.configuration, cluster_service=self.uc.container.get(ClusterService)
        )

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
            "rules": [],
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
            "rules": [],
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
            "rules": [],
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
            "rules": [],
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
        expected_job_params = {"ansible_tags": "ansible_tag1, ansible_tag2", "jinja2_native": True, "rules": []}

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


class TestActionLogic(BaseTestCase, TaskTestMixin):
    def setUp(self) -> None:
        super().setUp()
        bundles_dir = self.base_dir / "python" / "cm" / "tests" / "bundles"

        cluster_bundle = self.uc.upload_bundle(bundles_dir / "cluster_1")
        provider_bundle = self.uc.upload_bundle(bundles_dir / "provider")

        self.provider = self.uc.add_provider(bundle=provider_bundle, name="Test provider")
        self.cluster = self.uc.add_cluster(bundle=cluster_bundle, name="Test cluster")

        self.host_1 = self.uc.add_host(provider=self.provider, fqdn="host1", cluster=self.cluster)
        self.host_2 = self.uc.add_host(provider=self.provider, fqdn="host2", cluster=self.cluster)
        self.host_3 = self.uc.add_host(provider=self.provider, fqdn="host3", cluster=self.cluster)
        self.host_4 = self.uc.add_host(provider=self.provider, fqdn="host4", cluster=self.cluster)

        self.service, *_ = self.uc.add_services_to_cluster(cluster=self.cluster, names=["service_two_components"])
        self.component_1 = self.service.components.get(prototype__name="component_1")
        self.component_2 = self.service.components.get(prototype__name="component_2")

    def get_dummy_task_job(
        self, owner: Model | None, delta: TaskMappingDelta, rules: list[HcAclRule]
    ) -> tuple[object, object]:
        task, job = DummyObject(), DummyObject()

        owner_ = None
        if owner:
            owner_ = DummyObject()
            owner_.id = owner.id
            owner_.type = orm_object_to_core_type(owner)
            owner_.prototype_id = owner.prototype_id

            related_objects = DummyObject()

            cluster = get_object_cluster(owner)
            cluster_ = None
            if cluster:
                cluster_ = DummyObject()
                cluster_.id = cluster.id
                cluster_.prototype_id = cluster.prototype_id

            related_objects.cluster = cluster_
            owner_.related_objects = related_objects

        task.owner = owner_
        task.action_process = None

        hostcomponent = DummyObject()
        hostcomponent.mapping_delta = delta
        task.hostcomponent = hostcomponent

        params = DummyObject()
        params.rules = rules
        job.params = params

        return task, job

    def get_fake_config_apply_task_job(self, owner: Model, parameter: str, value: object) -> tuple[object, object]:
        task, job = DummyObject(), DummyObject()
        owner_ = DummyObject()
        owner_.id = owner.id
        owner_.type = orm_object_to_core_type(owner)
        owner_.prototype_id = owner.prototype_id

        task.owner = owner_
        task.selector = {ADCMCoreType.CLUSTER.value: {"id": self.cluster.id, "name": self.cluster.name}}
        task.display_name = "Config apply"

        params = DummyObject()
        params.changes = [
            {
                "object": {"type": ADCMCoreType.CLUSTER.value},
                "parameters": [{"key": parameter, "value": value}],
            }
        ]

        job.id = 111
        job.params = params

        return task, job

    def test_internal_hc_apply(self):
        cluster_service = self.uc.container.get(ClusterService)
        service_name = self.service.prototype.name
        c1_name = self.component_1.prototype.name
        c2_name = self.component_2.prototype.name

        # h1-c1, h2-c1, h3-c2
        initial_hc = ((self.host_1, self.component_1), (self.host_2, self.component_1), (self.host_3, self.component_2))
        self.uc.set_hostcomponent(cluster=self.cluster, entries=initial_hc)

        # Case 1. rules specifies changes not present in mapping_delta
        mapping_delta = TaskMappingDelta(
            add={self.component_2.pk: {self.host_4.pk}}, remove={self.component_1.pk: {self.host_1.pk, self.host_2.pk}}
        )
        rules = [HcAclRule(service=service_name, component=c1_name, action="add")]
        task, job = self.get_dummy_task_job(owner=self.cluster, delta=mapping_delta, rules=rules)

        result = internal_script_hc_apply(task=task, job=job, cluster_service=cluster_service)
        actual_hc = set(HostComponent.objects.filter(cluster_id=self.cluster.pk).values_list("host_id", "component_id"))
        expected_hc = {(host.pk, component.pk) for host, component in initial_hc}
        self.assertSetEqual(actual_hc, expected_hc)

        expected_message = "The script `hc_apply` completed successfully, but the component mapping was done earlier."
        self.assertEqual(result.message, expected_message)
        self.assertEqual(result.code, 0)

        # Case 2. rules specifies changes partially present in mapping_delta
        mapping_delta = TaskMappingDelta(
            remove={self.component_1.pk: {self.host_1.pk}, self.component_2.pk: {self.host_3.pk}}
        )
        rules = [
            HcAclRule(service=service_name, component=c1_name, action="remove"),  # in delta
            HcAclRule(service=service_name, component=c2_name, action="add"),  # not in delta
        ]
        task, job = self.get_dummy_task_job(owner=self.cluster, delta=mapping_delta, rules=rules)

        result = internal_script_hc_apply(task=task, job=job, cluster_service=cluster_service)
        actual_hc = set(HostComponent.objects.filter(cluster_id=self.cluster.pk).values_list("host_id", "component_id"))
        expected_hc = {(self.host_2.pk, self.component_1.pk), (self.host_3.pk, self.component_2.pk)}
        self.assertSetEqual(actual_hc, expected_hc)

        expected_message = "The script `hc_apply` completed successfully, the component mapping is complete."
        self.assertEqual(result.message, expected_message)
        self.assertEqual(result.code, 0)

        # restore HC
        self.uc.set_hostcomponent(cluster=self.cluster, entries=initial_hc)

        # Case 3. mapping_delta is partially specified in rules
        mapping_delta = TaskMappingDelta(
            add={self.component_2.pk: {self.host_1.pk, self.host_4.pk}}, remove={self.component_1.pk: {self.host_1.pk}}
        )
        rules = [
            HcAclRule(service=service_name, component=c2_name, action="add"),
            HcAclRule(service=service_name, component="nonexistent_component", action="add"),
        ]
        task, job = self.get_dummy_task_job(owner=self.cluster, delta=mapping_delta, rules=rules)

        internal_script_hc_apply(task=task, job=job, cluster_service=cluster_service)
        actual_hc = set(HostComponent.objects.filter(cluster_id=self.cluster.pk).values_list("host_id", "component_id"))
        expected_hc = {
            (self.host_1.pk, self.component_1.pk),
            (self.host_2.pk, self.component_1.pk),
            (self.host_1.pk, self.component_2.pk),
            (self.host_3.pk, self.component_2.pk),
            (self.host_4.pk, self.component_2.pk),
        }
        self.assertSetEqual(actual_hc, expected_hc)

        task, job = self.get_dummy_task_job(owner=self.provider, delta=mapping_delta, rules=rules)
        with self.assertRaises(AdcmEx):
            internal_script_hc_apply(task=task, job=job, cluster_service=cluster_service)

    def test_adcm_7918_internal_config_apply_result(self):
        update_configuration_from_job = self.uc.container.get(UpdateConfigurationFromJob)
        expected_value = "changed"
        parameter = "/string"
        task, job = self.get_fake_config_apply_task_job(owner=self.cluster, parameter=parameter, value=expected_value)

        with patch("use_cases.transition.config.update_related_configs"):
            result = internal_script_config_apply(
                task=task,
                job=job,
                update_configuration_from_job=update_configuration_from_job,
            )

            expected_message = "The script `config_apply` completed successfully, the configuration updates are done."
            self.assertEqual(result.code, 0)
            self.assertEqual(result.message, expected_message)

            # check the completed message after an attempt to apply the current configs
            result = internal_script_config_apply(
                task=task,
                job=job,
                update_configuration_from_job=update_configuration_from_job,
            )

        expected_message = (
            "The script `config_apply` completed successfully, but the configuration was updated earlier."
        )
        self.assertEqual(result.code, 0)
        self.assertEqual(result.message, expected_message)

    def get_dummy_service_manage_task_job(
        self,
        owner: Model | None,
        services: list[dict],
        action_process: CallingProcess | AssociatedProcess | None = None,
    ) -> tuple[object, object]:
        task, job = DummyObject(), DummyObject()

        owner_ = None
        if owner:
            owner_ = DummyObject()
            owner_.id = owner.id
            owner_.type = orm_object_to_core_type(owner)
            owner_.prototype_id = owner.prototype_id

            related_objects = DummyObject()

            cluster = get_object_cluster(owner)
            cluster_ = None
            if cluster:
                cluster_ = DummyObject()
                cluster_.id = cluster.id
                cluster_.prototype_id = cluster.prototype_id

            related_objects.cluster = cluster_
            owner_.related_objects = related_objects

        task.owner = owner_
        task.action_process = action_process
        task.display_name = "Service manage"

        params = DummyObject()
        params.operation = "add"
        params.services = [ServiceManageServiceEntry.model_validate(entry) for entry in services]
        job.params = params
        job.id = 112

        return task, job

    def get_service_manage_deps(self) -> dict:
        return {"manage_services": self.uc.container.get(ManageClusterServices)}

    def test_internal_service_manage_add_success(self):
        task, job = self.get_dummy_service_manage_task_job(
            owner=self.cluster,
            services=[{"name": "another_service_two_components"}, {"name": "another_service_two_components_2"}],
        )

        with patch("use_cases.transition.service_manage.create_related_configs") as related_configs_mock:
            result = internal_script_service_manage(task=task, job=job, **self.get_service_manage_deps())

        self.assertEqual(result.code, 0)
        self.assertIn("services are in place", result.message)

        for name in ("another_service_two_components", "another_service_two_components_2"):
            service = Service.objects.filter(cluster=self.cluster, prototype__name=name).first()
            self.assertIsNotNone(service)
            self.assertEqual(Component.objects.filter(service=service).count(), 2)
            self.assertIsNotNone(service.config)

        related_configs_mock.assert_called_once_with(job_id=job.id, owner=task.owner)

    def test_internal_service_manage_add_existing_service_success(self):
        task, job = self.get_dummy_service_manage_task_job(
            owner=self.cluster, services=[{"name": "service_two_components"}]
        )

        with patch("use_cases.transition.service_manage.create_related_configs") as related_configs_mock:
            result = internal_script_service_manage(task=task, job=job, **self.get_service_manage_deps())

        self.assertEqual(result.code, 0)
        self.assertIn("already in place", result.message)
        self.assertEqual(
            Service.objects.filter(cluster=self.cluster, prototype__name="service_two_components").count(), 1
        )
        related_configs_mock.assert_not_called()

    def test_internal_service_manage_from_service_context_success(self):
        task, job = self.get_dummy_service_manage_task_job(
            owner=self.service, services=[{"name": "another_service_two_components"}]
        )

        with patch("use_cases.transition.service_manage.create_related_configs"):
            result = internal_script_service_manage(task=task, job=job, **self.get_service_manage_deps())

        self.assertEqual(result.code, 0)
        self.assertTrue(
            Service.objects.filter(cluster=self.cluster, prototype__name="another_service_two_components").exists()
        )

    def test_internal_service_manage_unknown_service_fail(self):
        task, job = self.get_dummy_service_manage_task_job(
            owner=self.cluster, services=[{"name": "nonexistent_service"}]
        )

        with self.assertRaises(AdcmEx) as err:
            internal_script_service_manage(task=task, job=job, **self.get_service_manage_deps())

        self.assertEqual(err.exception.code, "PROTOTYPE_NOT_FOUND")
        self.assertIn("nonexistent_service", err.exception.msg)

    def test_internal_service_manage_with_parameters_success(self):
        expected_value = "changed_by_service_manage"
        task, job = self.get_dummy_service_manage_task_job(
            owner=self.cluster,
            services=[
                {
                    "name": "another_service_two_components",
                    "config_changes": [{"key": "/string", "value": expected_value}],
                }
            ],
        )

        with (
            patch("use_cases.transition.service_manage.create_related_configs"),
            patch("use_cases.transition.config.update_related_configs"),
        ):
            result = internal_script_service_manage(task=task, job=job, **self.get_service_manage_deps())

        self.assertEqual(result.code, 0)
        service = Service.objects.get(cluster=self.cluster, prototype__name="another_service_two_components")
        current_config = ConfigLog.objects.get(obj_ref=service.config, id=service.config.current)
        self.assertEqual(current_config.config["string"], expected_value)

    def test_internal_service_manage_with_mapping_success(self):
        services = [
            {
                "name": "another_service_two_components",
                "hc_changes": [
                    {"component": "component_1", "hosts": ["host1", "host2"]},
                    {"component": "component_2", "hosts": ["host1"]},
                ],
            }
        ]
        task, job = self.get_dummy_service_manage_task_job(owner=self.cluster, services=services)

        with patch("use_cases.transition.service_manage.create_related_configs"):
            result = internal_script_service_manage(task=task, job=job, **self.get_service_manage_deps())

        self.assertEqual(result.code, 0)
        service = Service.objects.get(cluster=self.cluster, prototype__name="another_service_two_components")
        component_1 = Component.objects.get(service=service, prototype__name="component_1")
        component_2 = Component.objects.get(service=service, prototype__name="component_2")
        actual_hc = set(
            HostComponent.objects.filter(cluster=self.cluster, service=service).values_list("host_id", "component_id")
        )
        expected_hc = {
            (self.host_1.pk, component_1.pk),
            (self.host_2.pk, component_1.pk),
            (self.host_1.pk, component_2.pk),
        }
        self.assertSetEqual(actual_hc, expected_hc)

        # repeated call with the same arguments should change nothing
        task, job = self.get_dummy_service_manage_task_job(owner=self.cluster, services=services)
        with patch("use_cases.transition.service_manage.create_related_configs"):
            result = internal_script_service_manage(task=task, job=job, **self.get_service_manage_deps())

        self.assertEqual(result.code, 0)
        self.assertIn("already in place", result.message)
        self.assertEqual(HostComponent.objects.filter(cluster=self.cluster, service=service).count(), 3)

    def test_internal_service_manage_unknown_host_rollback_fail(self):
        task, job = self.get_dummy_service_manage_task_job(
            owner=self.cluster,
            services=[
                {
                    "name": "another_service_two_components",
                    "hc_changes": [{"component": "component_1", "hosts": ["nonexistent-host"]}],
                }
            ],
        )

        with (
            patch("use_cases.transition.service_manage.create_related_configs"),
            self.assertRaises(AdcmEx) as err,
        ):
            internal_script_service_manage(task=task, job=job, **self.get_service_manage_deps())

        self.assertEqual(err.exception.code, "HOST_NOT_FOUND")
        self.assertFalse(
            Service.objects.filter(cluster=self.cluster, prototype__name="another_service_two_components").exists()
        )

    def test_internal_service_manage_unknown_component_fail(self):
        task, job = self.get_dummy_service_manage_task_job(
            owner=self.cluster,
            services=[
                {
                    "name": "another_service_two_components",
                    "hc_changes": [{"component": "nonexistent_component", "hosts": ["host1"]}],
                }
            ],
        )

        with (
            patch("use_cases.transition.service_manage.create_related_configs"),
            self.assertRaises(AdcmEx) as err,
        ):
            internal_script_service_manage(task=task, job=job, **self.get_service_manage_deps())

        self.assertEqual(err.exception.code, "COMPONENT_NOT_FOUND")

    def test_service_manage_job_params_serialization(self):
        params = JobParams(
            ansible_tags="",
            operation="add",
            services=[
                {
                    "name": "some_service",
                    "config_changes": [{"key": "/some_param", "value": "some_value"}],
                    "hc_changes": [{"component": "some_component", "hosts": ["host-1"]}],
                }
            ],
        )

        self.assertEqual(params.operation, "add")
        entry = params.services[0]
        self.assertIsInstance(entry, ServiceManageServiceEntry)
        self.assertEqual(entry.config_changes[0].key, "/some_param")
        self.assertEqual(entry.hc_changes[0].hosts, ["host-1"])

        # fields are excluded from serialization to keep rendered job params (e.g. job's `config.json`) unchanged
        dumped = params.model_dump()
        self.assertNotIn("operation", dumped)
        self.assertNotIn("services", dumped)

        # only `add` operation exists for now
        with self.assertRaises(ValidationError):
            JobParams(ansible_tags="", operation="remove")

    def test_internal_service_manage_mapping_to_mm_host_fail(self):
        Host.objects.filter(pk=self.host_1.pk).update(maintenance_mode=MaintenanceMode.ON)

        task, job = self.get_dummy_service_manage_task_job(
            owner=self.cluster,
            services=[
                {
                    "name": "another_service_two_components",
                    "hc_changes": [{"component": "component_1", "hosts": ["host1"]}],
                }
            ],
        )

        with (
            patch("use_cases.transition.service_manage.create_related_configs"),
            self.assertRaises(AdcmEx) as err,
        ):
            internal_script_service_manage(task=task, job=job, **self.get_service_manage_deps())

        self.assertEqual(err.exception.code, "INVALID_HC_HOST_IN_MM")
        self.assertFalse(
            Service.objects.filter(cluster=self.cluster, prototype__name="another_service_two_components").exists()
        )

    def test_internal_service_manage_absent_service_in_mapping_fail(self):
        topology = self.uc.container.get(ClusterService).retrieve_topology(cluster_id=self.cluster.pk)
        entries = (
            ServiceManageServiceEntry(
                name="ghost_service", hc_changes=[{"component": "component_1", "hosts": ["host1"]}]
            ),
        )

        with self.assertRaises(AdcmEx) as err:
            _build_mapping_delta(topology=topology, entries=entries)

        self.assertEqual(err.exception.code, "SERVICE_NOT_FOUND")
        self.assertIn("ghost_service", err.exception.msg)

    def test_internal_service_manage_from_wizard_operation_step_success(self):
        task, job = self.get_dummy_service_manage_task_job(
            owner=self.cluster,
            services=[{"name": "another_service_two_components"}],
            action_process=CallingProcess(id=1, sync_key=uuid4(), step_id=2),
        )

        with patch("use_cases.transition.service_manage.create_related_configs"):
            result = internal_script_service_manage(task=task, job=job, **self.get_service_manage_deps())

        self.assertEqual(result.code, 0)
        self.assertTrue(
            Service.objects.filter(cluster=self.cluster, prototype__name="another_service_two_components").exists()
        )

    def test_internal_service_manage_from_wizard_completing_action_success(self):
        task, job = self.get_dummy_service_manage_task_job(
            owner=self.cluster,
            services=[{"name": "another_service_two_components"}],
            action_process=AssociatedProcess(id=1),
        )

        with patch("use_cases.transition.service_manage.create_related_configs"):
            result = internal_script_service_manage(task=task, job=job, **self.get_service_manage_deps())

        self.assertEqual(result.code, 0)
        self.assertTrue(
            Service.objects.filter(cluster=self.cluster, prototype__name="another_service_two_components").exists()
        )
