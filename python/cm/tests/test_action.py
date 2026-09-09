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
    ClusterHostSource,
    ComponentHostSource,
    ConfigApplyChangeEntry,
    ConfigApplyParameterEntry,
    ConfigHostGroupSource,
    HcAclRule,
    HostComponentChanges,
    HostGroupEntry,
    HostGroupManageScriptParams,
    HostGroupParameter,
    HostGroupReference,
    HostManageScriptParams,
    ServiceManageScriptParams,
    ServiceManageServiceEntry,
    ServiceObjectTarget,
    TargetCluster,
    TaskMappingDelta,
    TypeBasedConfigApplyTarget,
    TypeBasedObjectTarget,
)
from core.action.job import JobShortFilter
from core.action.operations import flatten_execution_plan, to_rich_jobs
from core.cluster import ClusterService
from core.config import ConfigRepoI, ConfigService
from core.legacy.job.runners import (
    ADCMSettings,
    AnsibleSettings,
    ConsulSettings,
    ExternalSettings,
    IntegrationsSettings,
)
from core.types import ADCMCoreType, ADCMHostGroupType, Descriptor
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.models import Model
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from pydantic import TypeAdapter, ValidationError
from rbac.scenarios import RBACScenarios
from rest_framework.status import HTTP_200_OK
from tests.base import BaseTestCase
from tests.deprecated import TaskTestMixin
from tests.suites import ADCMDjangoAPISuite
from use_cases.transition.config import UpdateConfigurationFromJob, UpdateHostGroupConfigurationFromJob
from use_cases.transition.service_manage import ManageClusterServices, _build_mapping_delta

from cm.converters import orm_object_to_core_type
from cm.errors import AdcmEx
from cm.impl.job.repo import JobRepo
from cm.legacy.services.job.run.target_factories import (
    internal_script_config_apply,
    internal_script_hc_apply,
    internal_script_host_group_manage,
    internal_script_host_manage,
    internal_script_service_manage,
    prepare_ansible_environment,
)
from cm.models import (
    Action,
    ActionHostGroup,
    Component,
    ConfigHostGroup,
    ConfigLog,
    Host,
    HostComponent,
    MaintenanceMode,
    ObjectConfig,
    Service,
    TaskLog,
    get_object_cluster,
)
from cm.transition.status import StatusScenarios


def set_dummy_job_spec(job: object, params: object) -> None:
    """Give a dummy job the bits of a plan node the internal scripts read"""

    script = DummyObject()
    script.params = params

    spec = DummyObject()
    spec.script = script

    job.spec = spec


class DummyObject:
    pass


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

        repo = JobRepo()
        task = repo.get_task(id=response.json()["id"])

        plan = repo.get_execution_plan(task_id=task.id)
        task_jobs = repo.find_jobs_short(JobShortFilter(task_ids=[task.id]))
        jobs_by_key = to_rich_jobs(spec=plan, jobs=task_jobs)
        job, *_ = (jobs_by_key[key] for key in flatten_execution_plan(plan))

        job_dir: Path = self.directories.run / str(job.runtime.id)
        job_dir.mkdir(parents=True)
        prepare_ansible_environment(
            task=task,
            job=job,
            configuration=self.configuration,
            cluster_service=self.uc.container.get(ClusterService),
            config_service=self.uc.container.get(ConfigService),
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
        set_dummy_job_spec(job, params)

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
            ConfigApplyChangeEntry(
                object=TypeBasedConfigApplyTarget(type=ADCMCoreType.CLUSTER.value),
                parameters=[ConfigApplyParameterEntry(key=parameter, value=value)],
            )
        ]

        job.runtime = DummyObject()
        job.runtime.id = 111
        set_dummy_job_spec(job, params)

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
        set_dummy_job_spec(job, params)
        job.runtime = DummyObject()
        job.runtime.id = 112

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

        related_configs_mock.assert_called_once_with(
            job_id=job.runtime.id, owner=task.owner, config_repo=self.uc.container.get(ConfigRepoI)
        )

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

    def test_internal_service_manage_existing_service_changes_skipped(self):
        initial_config = ConfigLog.objects.get(obj_ref=self.service.config, id=self.service.config.current)
        task, job = self.get_dummy_service_manage_task_job(
            owner=self.cluster,
            services=[
                {
                    "name": "service_two_components",
                    "config_changes": [{"key": "/string", "value": "should_not_be_applied"}],
                    "hc_changes": [{"component": "component_1", "hosts": ["host1"]}],
                }
            ],
        )

        with (
            patch("use_cases.transition.service_manage.create_related_configs") as related_configs_mock,
            patch("use_cases.transition.config.update_related_configs"),
        ):
            result = internal_script_service_manage(task=task, job=job, **self.get_service_manage_deps())

        self.assertEqual(result.code, 0)
        self.assertIn("already in place", result.message)
        related_configs_mock.assert_not_called()

        # neither configuration nor mapping of an already present service should be touched
        self.service.config.refresh_from_db()
        self.assertEqual(self.service.config.current, initial_config.id)
        self.assertFalse(HostComponent.objects.filter(cluster=self.cluster, service=self.service).exists())

    def test_internal_service_manage_mixed_new_and_existing_services_success(self):
        expected_value = "changed_by_service_manage"
        initial_config = ConfigLog.objects.get(obj_ref=self.service.config, id=self.service.config.current)
        task, job = self.get_dummy_service_manage_task_job(
            owner=self.cluster,
            services=[
                {
                    "name": "service_two_components",
                    "config_changes": [{"key": "/string", "value": "should_not_be_applied"}],
                    "hc_changes": [{"component": "component_1", "hosts": ["host1"]}],
                },
                {
                    "name": "another_service_two_components",
                    "config_changes": [{"key": "/string", "value": expected_value}],
                    "hc_changes": [{"component": "component_1", "hosts": ["host2"]}],
                },
            ],
        )

        with (
            patch("use_cases.transition.service_manage.create_related_configs"),
            patch("use_cases.transition.config.update_related_configs"),
        ):
            result = internal_script_service_manage(task=task, job=job, **self.get_service_manage_deps())

        self.assertEqual(result.code, 0)

        # the added service gets both its configuration and mapping changes
        added_service = Service.objects.get(cluster=self.cluster, prototype__name="another_service_two_components")
        added_config = ConfigLog.objects.get(obj_ref=added_service.config, id=added_service.config.current)
        self.assertEqual(added_config.config["string"], expected_value)
        added_component_1 = Component.objects.get(service=added_service, prototype__name="component_1")
        self.assertSetEqual(
            set(HostComponent.objects.filter(cluster=self.cluster).values_list("host_id", "component_id")),
            {(self.host_2.pk, added_component_1.pk)},
        )

        # the already present service is left as is
        self.service.config.refresh_from_db()
        self.assertEqual(self.service.config.current, initial_config.id)

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

    def test_service_manage_script_params_validation(self):
        params = TypeAdapter(ServiceManageScriptParams).validate_python(
            {
                "operation": "add",
                "services": [
                    {
                        "name": "some_service",
                        "config_changes": [{"key": "/some_param", "value": "some_value"}],
                        "hc_changes": [{"component": "some_component", "hosts": ["host-1"]}],
                    }
                ],
            }
        )

        self.assertEqual(params.operation, "add")
        entry = params.services[0]
        self.assertIsInstance(entry, ServiceManageServiceEntry)
        self.assertEqual(entry.config_changes[0].key, "/some_param")
        self.assertEqual(entry.hc_changes[0].hosts, ["host-1"])

        # only `add` operation exists for now
        with self.assertRaises(ValidationError):
            TypeAdapter(ServiceManageScriptParams).validate_python({"operation": "remove", "services": []})

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


class TestHostManageInternalScripts(BaseTestCase, TaskTestMixin):
    """The `host_manage` and `host_group_manage` internal scripts"""

    def setUp(self) -> None:
        super().setUp()
        bundles_dir = self.base_dir / "python" / "cm" / "tests" / "bundles"

        cluster_bundle = self.uc.upload_bundle(bundles_dir / "cluster_1")
        provider_bundle = self.uc.upload_bundle(bundles_dir / "provider")

        self.provider = self.uc.add_provider(bundle=provider_bundle, name="Test provider")

        self.source = self.uc.add_cluster(bundle=cluster_bundle, name="Source cluster")
        self.source_service, *_ = self.uc.add_services_to_cluster(cluster=self.source, names=["service_two_components"])
        self.source_component = self.source_service.components.get(prototype__name="component_1")
        self.source_host_1 = self.uc.add_host(provider=self.provider, fqdn="shared-1", cluster=self.source)
        self.source_host_2 = self.uc.add_host(provider=self.provider, fqdn="shared-2", cluster=self.source)
        self.uc.set_hostcomponent(
            cluster=self.source,
            entries=[(self.source_host_1, self.source_component), (self.source_host_2, self.source_component)],
        )

        self.target = self.uc.add_cluster(bundle=cluster_bundle, name="Target cluster")
        self.service, *_ = self.uc.add_services_to_cluster(cluster=self.target, names=["service_two_components"])
        self.component_1 = self.service.components.get(prototype__name="component_1")
        self.service_name = self.service.prototype.name

        self.config_service = self.uc.container.get(ConfigService)
        self.cluster_service = self.uc.container.get(ClusterService)
        self.rbac_scenarios = self.uc.container.get(RBACScenarios)
        self.status_scenarios = self.uc.container.get(StatusScenarios)
        self.update_host_group_configuration = self.uc.container.get(UpdateHostGroupConfigurationFromJob)

        self.owner = ServiceObjectTarget(type="service", service_name=self.service_name)

    # harness

    def make_task(self, delta: TaskMappingDelta | None = None) -> object:
        task = DummyObject()

        owner = DummyObject()
        owner.id = self.service.id
        owner.type = orm_object_to_core_type(self.service)
        owner.prototype_id = self.service.prototype_id

        related_objects = DummyObject()
        cluster = DummyObject()
        cluster.id = self.target.id
        cluster.prototype_id = self.target.prototype_id
        related_objects.cluster = cluster
        related_objects.provider = None
        owner.related_objects = related_objects

        task.id = self.task_id
        task.owner = owner
        task.config = None
        task.display_name = "Attach"
        task.hostcomponent = HostComponentChanges(post_upgrade=None, mapping_delta=delta)
        task.selector = {
            "cluster": {"id": self.target.id, "name": self.target.name},
            "service": {"id": self.service.id, "name": self.service_name},
        }

        return task

    @property
    def task_id(self) -> int:
        """A real TaskLog row, because the delta these scripts write is stored on one."""

        if not hasattr(self, "_task_id"):
            self._task_id = TaskLog.objects.create(
                object_id=self.target.pk,
                object_type=ContentType.objects.get_for_model(self.target),
                status="running",
                selector={},
            ).pk

        return self._task_id

    def make_job(self, params: object) -> object:
        job = DummyObject()
        job.runtime = DummyObject()
        job.runtime.id = 999
        set_dummy_job_spec(job, params)

        return job

    def run_host_manage(self, task: object | None = None, **params):
        task = task if task is not None else self.make_task()

        return internal_script_host_manage(
            task=task,
            job=self.make_job(HostManageScriptParams(**params)),
            config_service=self.config_service,
            rbac_scenarios=self.rbac_scenarios,
            status_scenarios=self.status_scenarios,
            cluster_service=self.cluster_service,
        )

    def run_group_manage(self, task: object | None = None, **params):
        return internal_script_host_group_manage(
            task=task if task is not None else self.make_task(),
            job=self.make_job(HostGroupManageScriptParams(**params)),
            rbac_scenarios=self.rbac_scenarios,
            config_service=self.config_service,
            update_host_group_configuration=self.update_host_group_configuration,
        )

    def whole_source_cluster(self) -> list:
        return [ClusterHostSource(type="cluster", cluster_name=self.source.name)]

    def add_duplicates(self, task: object | None = None, **extra):
        return self.run_host_manage(task=task, operation="add_duplicates", source=self.whole_source_cluster(), **extra)

    def target_duplicates(self) -> dict[str, Host]:
        return {host.fqdn: host for host in Host.objects.filter(cluster=self.target, original__isnull=False)}

    def map_duplicates(self) -> None:
        self.uc.set_hostcomponent(
            cluster=self.target,
            entries=[(host, self.component_1) for host in self.target_duplicates().values()],
        )

    def group_config(self, group: ConfigHostGroup) -> dict:
        """The group's own current configuration values."""

        return self.config_service.retrieve_current_configuration(
            owner=Descriptor(id=group.pk, type=ADCMHostGroupType.CONFIG)
        ).values

    def group_of(self, name: str, description: str = "", **extra) -> HostGroupEntry:
        return HostGroupEntry(name=name, type="config_host_group", object=self.owner, description=description, **extra)

    # add_duplicates

    def test_add_duplicates(self):
        result = self.add_duplicates()

        self.assertEqual(result.code, 0)
        self.assertIn("2 created, 0 already here", result.message)

        duplicates = self.target_duplicates()
        self.assertEqual(set(duplicates), {"shared-1", "shared-2"})
        self.assertEqual(duplicates["shared-1"].original_id, self.source_host_1.pk)

        # originals stayed with the source cluster
        self.source_host_1.refresh_from_db()
        self.assertEqual(self.source_host_1.cluster_id, self.source.pk)

        # re-run changes nothing and says so
        result = self.add_duplicates()
        self.assertIn("but the hosts were duplicated earlier", result.message)
        self.assertEqual(len(self.target_duplicates()), 2)

    def test_add_duplicates_by_component(self):
        result = self.run_host_manage(
            operation="add_duplicates",
            source=[
                ComponentHostSource(
                    type="component",
                    cluster_name=self.source.name,
                    service_name=self.source_service.prototype.name,
                    component_name=self.source_component.prototype.name,
                )
            ],
        )

        self.assertEqual(result.code, 0)
        self.assertEqual(set(self.target_duplicates()), {"shared-1", "shared-2"})

    def test_add_duplicates_identity_is_the_original_not_the_name(self):
        """A duplicate can be renamed; that must not make a re-run create a second copy."""

        self.add_duplicates()
        duplicate = self.target_duplicates()["shared-1"]
        duplicate.fqdn = "renamed"
        duplicate.save(update_fields=["fqdn"])

        result = self.add_duplicates()

        self.assertIn("but the hosts were duplicated earlier", result.message)
        self.assertEqual(Host.objects.filter(cluster=self.target, original__isnull=False).count(), 2)

    def test_add_duplicates_skips_a_host_the_target_already_owns(self):
        """A cluster does not hold a copy of a host it already has in its own right."""

        native = self.uc.add_host(provider=self.provider, fqdn="native-1", cluster=self.target)

        # both clusters at once, so the count proves the native host was recognised as already
        # here rather than the selector simply resolving to nothing
        result = self.run_host_manage(
            operation="add_duplicates",
            source=[
                ClusterHostSource(type="cluster", cluster_name=self.target.name),
                ClusterHostSource(type="cluster", cluster_name=self.source.name),
            ],
        )

        self.assertEqual(result.code, 0)
        self.assertIn("2 created, 1 already here", result.message)
        self.assertEqual(set(self.target_duplicates()), {"shared-1", "shared-2"})
        native.refresh_from_db()
        self.assertEqual(native.cluster_id, self.target.pk)
        self.assertIsNone(native.original_id)

    def test_add_duplicates_into_a_named_target(self):
        third = self.uc.add_cluster(bundle=self.source.prototype.bundle, name="Third cluster")

        result = self.add_duplicates(target=[TargetCluster(cluster_name=third.name)])

        self.assertEqual(result.code, 0)
        self.assertEqual(self.target_duplicates(), {})
        self.assertEqual(Host.objects.filter(cluster=third, original__isnull=False).count(), 2)

    def test_add_duplicates_unknown_source_cluster_fail(self):
        with self.assertRaises(AdcmEx) as err:
            self.run_host_manage(
                operation="add_duplicates",
                source=[ClusterHostSource(type="cluster", cluster_name="no-such-cluster")],
            )

        self.assertIn("no-such-cluster", err.exception.msg)
        self.assertEqual(self.target_duplicates(), {})

    def test_add_duplicates_query_count_does_not_grow_with_hosts(self):
        """Duplicating ten hosts costs what duplicating two costs.

        The absolute number is not asserted: joining a cluster re-applies that cluster's
        policies, whose cost belongs to the cluster. What must hold is that the number of hosts
        being duplicated does not enter into it.
        """

        few = self.count_add_queries(label="few", hosts=2)
        many = self.count_add_queries(label="many", hosts=10)

        self.assertEqual(few, many)

    def count_add_queries(self, label: str, hosts: int) -> int:
        bundle = self.source.prototype.bundle
        scratch_target = self.uc.add_cluster(bundle=bundle, name=f"Scratch target {label}")
        scratch_source = self.uc.add_cluster(bundle=bundle, name=f"Scratch source {label}")
        for index in range(hosts):
            self.uc.add_host(provider=self.provider, fqdn=f"scratch-{label}-{index}", cluster=scratch_source)

        task = self.make_task()
        task.owner.related_objects.cluster.id = scratch_target.id

        with CaptureQueriesContext(connection) as captured:
            self.run_host_manage(
                task=task,
                operation="add_duplicates",
                source=[ClusterHostSource(type="cluster", cluster_name=scratch_source.name)],
            )

        return len(captured)

    # mapping_rules

    def test_mapping_rules_write_the_delta_without_committing_it(self):
        task = self.make_task()

        result = self.add_duplicates(
            task=task,
            mapping_rules=[HcAclRule(service=self.service_name, component="component_1", action="add")],
        )

        self.assertIn("2 mapping change(s) prepared", result.message)

        # nothing is mapped yet - `hc_apply` is what commits
        self.assertFalse(HostComponent.objects.filter(cluster=self.target).exists())

        # the delta reached both the task in memory (the sequential runner) and the database
        # (the celery runner and every later job's inventory)
        delta = task.hostcomponent.mapping_delta
        self.assertEqual(delta.add[self.component_1.pk], {host.pk for host in self.target_duplicates().values()})
        stored = JobRepo().get_task_mutable_fields(id=task.id).hostcomponent.mapping_delta
        self.assertEqual(stored.add[self.component_1.pk], delta.add[self.component_1.pk])

    def test_mapping_rules_only_record_the_difference(self):
        self.add_duplicates()
        self.map_duplicates()

        task = self.make_task()
        result = self.add_duplicates(
            task=task,
            mapping_rules=[HcAclRule(service=self.service_name, component="component_1", action="add")],
        )

        self.assertIn("but the hosts were duplicated earlier", result.message)
        self.assertIsNone(task.hostcomponent.mapping_delta)

    def test_mapping_rules_unknown_component_fail(self):
        with self.assertRaises(AdcmEx) as err:
            self.add_duplicates(
                mapping_rules=[HcAclRule(service=self.service_name, component="no_such_component", action="add")]
            )

        self.assertIn("no_such_component", err.exception.msg)

    # groups

    def test_host_group_manage_creates_updates_and_removes(self):
        result = self.run_group_manage(
            operation="add", groups=[self.group_of(name="adb-one", description="per-cluster settings")]
        )

        self.assertEqual(result.code, 0)
        self.assertIn("1 created", result.message)

        group = ConfigHostGroup.objects.get(object_id=self.service.pk, name="adb-one")
        self.assertEqual(group.description, "per-cluster settings")

        # re-run changes nothing and says so
        result = self.run_group_manage(
            operation="add", groups=[self.group_of(name="adb-one", description="per-cluster settings")]
        )
        self.assertIn("but the groups were set up earlier", result.message)

        # the description is declarative
        self.run_group_manage(operation="add", groups=[self.group_of(name="adb-one", description="changed")])
        group.refresh_from_db()
        self.assertEqual(group.description, "changed")

        config_id = group.config_id
        result = self.run_group_manage(operation="remove", groups=[self.group_of(name="adb-one")])
        self.assertIn("1 removed", result.message)
        self.assertFalse(ConfigHostGroup.objects.filter(object_id=self.service.pk, name="adb-one").exists())
        # the group's configuration goes with it instead of being orphaned
        self.assertFalse(ObjectConfig.objects.filter(id=config_id).exists())

        result = self.run_group_manage(operation="remove", groups=[self.group_of(name="adb-one")])
        self.assertIn("but the groups were removed earlier", result.message)

    def test_host_group_manage_creates_an_action_host_group(self):
        entry = HostGroupEntry(name="adb-one", type="action_host_group", object=self.owner)

        result = self.run_group_manage(operation="add", groups=[entry])

        self.assertEqual(result.code, 0)
        self.assertTrue(ActionHostGroup.objects.filter(object_id=self.service.pk, name="adb-one").exists())

        result = self.run_group_manage(operation="add", groups=[entry])
        self.assertIn("but the groups were set up earlier", result.message)

    def test_host_group_manage_tells_the_two_group_kinds_apart(self):
        """The two kinds are separate tables with separate id sequences, so ids collide."""

        self.add_duplicates()
        self.map_duplicates()

        action_group = HostGroupEntry(name="adb-one", type="action_host_group", object=self.owner)
        self.run_group_manage(operation="add", groups=[action_group, self.group_of(name="adb-one")])

        config_group = ConfigHostGroup.objects.get(object_id=self.service.pk, name="adb-one")
        action_group_row = ActionHostGroup.objects.get(object_id=self.service.pk, name="adb-one")
        # give them the same id, which is the state the two sequences produce on their own
        ActionHostGroup.objects.filter(pk=action_group_row.pk).update(id=config_group.pk)

        result = self.run_group_manage(
            operation="add",
            groups=[
                HostGroupEntry(
                    name="adb-one", type="action_host_group", object=self.owner, hosts=["shared-1", "shared-2"]
                )
            ],
        )

        self.assertIn("2 host(s) added", result.message)
        self.assertEqual(
            sorted(ActionHostGroup.objects.get(pk=config_group.pk).hosts.values_list("fqdn", flat=True)),
            ["shared-1", "shared-2"],
        )
        # the configuration group of the same id is untouched
        self.assertEqual(list(config_group.hosts.values_list("fqdn", flat=True)), [])

    def test_host_group_manage_desynchronises_a_parameter_already_equal_to_the_owner(self):
        """Writing the value the group already shows still has to detach it from the owner."""

        cluster_owner = TypeBasedObjectTarget(type="cluster")
        result = self.run_group_manage(
            operation="add",
            groups=[
                HostGroupEntry(
                    name="adb-one",
                    type="config_host_group",
                    object=cluster_owner,
                    # 10 is the owner's own value, so nothing about the group's config changes
                    parameters=[HostGroupParameter(key="integer", value=10)],
                )
            ],
        )

        self.assertEqual(result.code, 0)

        group = ConfigHostGroup.objects.get(object_id=self.target.pk, name="adb-one")
        self.uc.change_config(owner=self.target, values_diff={"integer": 7})

        config = self.group_config(group)
        self.assertEqual(config["integer"], 10)

    def test_host_group_manage_membership_is_three_state(self):
        self.add_duplicates()
        self.map_duplicates()

        self.run_group_manage(operation="add", groups=[self.group_of(name="adb-one")])
        group = ConfigHostGroup.objects.get(object_id=self.service.pk, name="adb-one")

        # a list replaces membership with exactly that set
        result = self.run_group_manage(operation="add", groups=[self.group_of(name="adb-one", hosts=["shared-1"])])
        self.assertIn("1 host(s) added", result.message)
        self.assertEqual(list(group.hosts.values_list("fqdn", flat=True)), ["shared-1"])

        result = self.run_group_manage(operation="add", groups=[self.group_of(name="adb-one", hosts=["shared-2"])])
        self.assertIn("1 host(s) added, 1 host(s) removed", result.message)
        self.assertEqual(list(group.hosts.values_list("fqdn", flat=True)), ["shared-2"])

        # omitted leaves membership alone
        self.run_group_manage(operation="add", groups=[self.group_of(name="adb-one")])
        self.assertEqual(list(group.hosts.values_list("fqdn", flat=True)), ["shared-2"])

        # an empty list empties it
        result = self.run_group_manage(operation="add", groups=[self.group_of(name="adb-one", hosts=[])])
        self.assertIn("1 host(s) removed", result.message)
        self.assertEqual(list(group.hosts.values_list("fqdn", flat=True)), [])

    def test_host_group_manage_moves_a_host_between_groups_of_one_owner(self):
        """A host belongs to one configuration group of an owner, so it has to leave first."""

        self.add_duplicates()
        self.map_duplicates()
        self.run_group_manage(
            operation="add",
            groups=[self.group_of(name="first", hosts=["shared-1"]), self.group_of(name="second")],
        )

        result = self.run_group_manage(
            operation="add",
            groups=[self.group_of(name="first", hosts=[]), self.group_of(name="second", hosts=["shared-1"])],
        )

        self.assertEqual(result.code, 0)
        second = ConfigHostGroup.objects.get(object_id=self.service.pk, name="second")
        self.assertEqual(list(second.hosts.values_list("fqdn", flat=True)), ["shared-1"])

    def test_host_group_manage_writes_parameters(self):
        cluster_owner = TypeBasedObjectTarget(type="cluster")

        def write(value: int):
            return self.run_group_manage(
                operation="add",
                groups=[
                    HostGroupEntry(
                        name="adb-one",
                        type="config_host_group",
                        object=cluster_owner,
                        parameters=[HostGroupParameter(key="integer", value=value)],
                    )
                ],
            )

        result = write(42)

        self.assertEqual(result.code, 0)
        self.assertIn("1 created", result.message)

        group = ConfigHostGroup.objects.get(object_id=self.target.pk, name="adb-one")
        config = self.group_config(group)
        self.assertEqual(config["integer"], 42)

        # a value already in place is not written again
        self.assertIn("but the groups were set up earlier", write(42).message)

        # and it is the group's own value: a change to the owner's configuration must not
        # overwrite it, which only holds if the parameter was desynchronised when it was set
        self.uc.change_config(owner=self.target, values_diff={"integer": 7})
        config = self.group_config(group)
        self.assertEqual(config["integer"], 42)

    def test_host_group_manage_unmapped_host_fail(self):
        self.add_duplicates()
        self.run_group_manage(operation="add", groups=[self.group_of(name="adb-one")])

        with self.assertRaises(AdcmEx) as err:
            self.run_group_manage(operation="add", groups=[self.group_of(name="adb-one", hosts=["shared-1"])])

        self.assertIn("shared-1", err.exception.msg)

    def test_add_to_groups_fills_membership_from_the_source(self):
        self.add_duplicates()
        self.map_duplicates()
        self.run_group_manage(operation="add", groups=[self.group_of(name="adb-one")])

        result = self.run_host_manage(
            operation="add_to_groups",
            source=self.whole_source_cluster(),
            groups=[HostGroupReference(name="adb-one", type="config_host_group", object=self.owner)],
        )

        self.assertEqual(result.code, 0)
        self.assertIn("2 membership(s) added", result.message)
        group = ConfigHostGroup.objects.get(object_id=self.service.pk, name="adb-one")
        self.assertEqual(sorted(group.hosts.values_list("fqdn", flat=True)), ["shared-1", "shared-2"])

        result = self.run_host_manage(
            operation="add_to_groups",
            source=self.whole_source_cluster(),
            groups=[HostGroupReference(name="adb-one", type="config_host_group", object=self.owner)],
        )
        self.assertIn("but the hosts were added to their groups earlier", result.message)

    def test_add_to_groups_takes_only_duplicates(self):
        """The source is intersected with this cluster's duplicates; its own hosts stay out."""

        self.add_duplicates()
        native = self.uc.add_host(provider=self.provider, fqdn="native-1", cluster=self.target)
        self.uc.set_hostcomponent(
            cluster=self.target,
            entries=[(host, self.component_1) for host in [*self.target_duplicates().values(), native]],
        )
        self.run_group_manage(operation="add", groups=[self.group_of(name="adb-one")])

        # the whole target cluster: two duplicates and one host that belongs to it natively
        result = self.run_host_manage(
            operation="add_to_groups",
            source=[ClusterHostSource(type="cluster", cluster_name=self.target.name)],
            groups=[HostGroupReference(name="adb-one", type="config_host_group", object=self.owner)],
        )

        self.assertIn("2 membership(s) added", result.message)
        group = ConfigHostGroup.objects.get(object_id=self.service.pk, name="adb-one")
        self.assertEqual(sorted(group.hosts.values_list("fqdn", flat=True)), ["shared-1", "shared-2"])

    def test_add_to_groups_missing_group_fail(self):
        self.add_duplicates()
        self.map_duplicates()

        with self.assertRaises(AdcmEx) as err:
            self.run_host_manage(
                operation="add_to_groups",
                source=self.whole_source_cluster(),
                groups=[HostGroupReference(name="never-created", type="config_host_group", object=self.owner)],
            )

        self.assertIn("never-created", err.exception.msg)

    # remove_duplicates

    def test_remove_duplicates_unmaps_and_deletes(self):
        self.add_duplicates()
        self.map_duplicates()

        result = self.run_host_manage(operation="remove_duplicates", source=self.whole_source_cluster())

        self.assertEqual(result.code, 0)
        self.assertIn("2 deleted", result.message)
        self.assertEqual(self.target_duplicates(), {})
        self.assertFalse(HostComponent.objects.filter(cluster=self.target).exists())

        # originals are untouched
        self.source_host_1.refresh_from_db()
        self.assertEqual(self.source_host_1.cluster_id, self.source.pk)

        result = self.run_host_manage(operation="remove_duplicates", source=self.whole_source_cluster())
        self.assertIn("but the duplicates were removed earlier", result.message)

    def test_remove_duplicates_through_a_group_after_the_source_is_gone(self):
        self.add_duplicates()
        self.map_duplicates()
        self.run_group_manage(operation="add", groups=[self.group_of(name="adb-one", hosts=["shared-1", "shared-2"])])

        # the source cluster is renamed: the duplicates can't be found through it any more,
        # but the group that tracks them still names them
        self.source.name = "renamed to break the trail"
        self.source.save(update_fields=["name"])

        result = self.run_host_manage(
            operation="remove_duplicates",
            source=[ConfigHostGroupSource(type="config_host_group", name="adb-one", object=self.owner)],
        )

        self.assertEqual(result.code, 0)
        self.assertIn("2 deleted", result.message)
        self.assertEqual(self.target_duplicates(), {})

    def test_remove_duplicates_through_a_group_that_was_never_created(self):
        """An interrupted attachment leaves either half missing; cleanup must survive both."""

        result = self.run_host_manage(
            operation="remove_duplicates",
            source=[ConfigHostGroupSource(type="config_host_group", name="never-created", object=self.owner)],
        )

        self.assertEqual(result.code, 0)
        self.assertIn("but the duplicates were removed earlier", result.message)

    def test_remove_duplicates_takes_its_hosts_out_of_the_task_delta(self):
        """The delta is applied once more at task end; a deleted host must not still be in it."""

        task = self.make_task()
        self.add_duplicates(
            task=task,
            mapping_rules=[HcAclRule(service=self.service_name, component="component_1", action="add")],
        )
        self.map_duplicates()

        self.run_host_manage(task=task, operation="remove_duplicates", source=self.whole_source_cluster())

        self.assertTrue(task.hostcomponent.mapping_delta.is_empty)
        stored = JobRepo().get_task_mutable_fields(id=task.id).hostcomponent.mapping_delta
        self.assertTrue(stored.is_empty)
