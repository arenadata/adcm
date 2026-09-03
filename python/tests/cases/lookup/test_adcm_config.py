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

"""
Behavior "freeze" of `adcm_config` lookup plugin.

Tests here describe current behavior as-is (including its quirks),
so that new implementation can be compared against it.

Ansible variables are passed as plain dicts "like Ansible have already prepared them",
no real inventory/hostvars rendering is involved.
"""

from pathlib import Path
from typing import Any
import copy

from ansible.errors import AnsibleError
from ansible.parsing.yaml.objects import AnsibleUnicode
from ansible.utils.unsafe_proxy import AnsibleUnsafeText
from ansible_collections.arenadata.adcm.plugins.lookup.adcm_config import (
    LookupModule,
    PluginResult,
    call_adcm_config_lookup,
    detect_target,
)
from cm.converters import orm_object_to_core_type
from cm.errors import AdcmEx
from cm.impl.job.repo import JobRepo
from cm.legacy.services.job.action import prepare_task_for_action
from cm.legacy.services.job.run import create_related_configs
from cm.models import Action, ADCMEntity, Cluster, ConfigLog, Host, Provider, Service
from core.action.job import TaskPayloadDTO
from core.types import ActionTargetDescriptor
from unittest_parametrize import ParametrizedTestCase, param, parametrize
import django.test

from tests.suites import _ADCMTestCase

BUNDLES_DIR = Path(__file__).parent / "bundles"


class TestAdcmConfigLookup(ParametrizedTestCase, _ADCMTestCase, django.test.TestCase):
    """
    Behavior of `adcm_config` lookup: arguments serialization, target detection and config change itself
    """

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls._initialize_roles_and_adcm()

        cls.cluster_bundle = cls.uc.upload_bundle(BUNDLES_DIR / "cluster_lookup_config")
        cls.provider_bundle = cls.uc.upload_bundle(BUNDLES_DIR / "provider_lookup_config")

        cls.cluster = cls.uc.add_cluster(bundle=cls.cluster_bundle, name="Cluster For Lookup")
        cls.service_1, cls.service_2 = sorted(
            cls.uc.add_services_to_cluster(["service_1", "service_2"], cluster=cls.cluster),
            key=lambda service: service.name,
        )

        cls.provider = cls.uc.add_provider(bundle=cls.provider_bundle, name="Provider For Lookup")
        cls.host = cls.uc.add_host(provider=cls.provider, fqdn="host-1")

        # config change is recorded in job's related configs, and those are a snapshot of owner's hierarchy:
        # cluster-owned job covers cluster/services/components, provider-owned one covers provider/hosts
        cls.cluster_job_id = cls.prepare_job(owner=cls.cluster)
        cls.provider_job_id = cls.prepare_job(owner=cls.provider)

    # Environment preparation

    @classmethod
    def prepare_job(cls, owner: Cluster | Provider) -> int:
        """
        Launch object's "dummy" action and prepare its first job the way real run does
        """
        action_id = Action.objects.values_list("id", flat=True).get(prototype_id=owner.prototype_id, name="dummy")
        task = prepare_task_for_action(
            target=ActionTargetDescriptor(id=owner.pk, type=orm_object_to_core_type(owner)),
            orm_owner=owner,
            orm_target=owner,
            action=action_id,
            payload=TaskPayloadDTO(),
        )

        job, *_ = JobRepo().get_task_jobs(task.id)
        # not a subject of these tests, but without this snapshot `update_config` fails to record its change
        create_related_configs(job_id=job.id, owner=task.owner)

        return job.id

    # Helpers

    def build_variables(
        self,
        job_id: int | None = None,
        cluster: bool = False,
        service_id: int | None = None,
        provider: bool = False,
        host: Host | None = None,
    ) -> dict[str, Any]:
        """
        Build ansible variables in the same shape lookup expects to receive them from hostvars
        """
        variables: dict[str, Any] = {}

        if job_id is not None:
            variables["job"] = {"id": job_id, "action": "dummy"}
            if service_id is not None:
                variables["job"]["service_id"] = service_id

        if cluster:
            variables["cluster"] = {"id": self.cluster.pk, "name": self.cluster.name}

        if provider:
            variables["provider"] = {"id": self.provider.pk, "name": self.provider.name}

        if host is not None:
            variables["adcm_hostid"] = host.pk

        return variables

    def call_lookup(self, *terms: Any, variables: dict[str, Any], **kwargs: Any) -> PluginResult:
        """
        Imitate `lookup('adcm_config', *terms, **kwargs)` call
        """
        return call_adcm_config_lookup(terms=list(terms), variables=variables, kwargs=kwargs)

    def get_config(self, object_: ADCMEntity) -> dict:
        object_.refresh_from_db(fields=["config"])

        return ConfigLog.objects.values_list("config", flat=True).get(id=object_.config.current)

    def get_config_log_amount(self, object_: ADCMEntity) -> int:
        return ConfigLog.objects.filter(obj_ref=object_.config).count()

    # Shortcuts for the most used variable sets

    @property
    def cluster_vars(self) -> dict[str, Any]:
        return self.build_variables(job_id=self.cluster_job_id, cluster=True)

    @property
    def provider_vars(self) -> dict[str, Any]:
        return self.build_variables(job_id=self.provider_job_id, provider=True)

    # Arguments serialization

    @parametrize(
        "terms",
        [
            param((), id="no_terms"),
            param(("cluster",), id="only_type"),
            param(("cluster", "plain_s"), id="type_and_key"),
        ],
    )
    def test_not_enough_terms_fail(self, terms: tuple) -> None:
        with self.assertRaises(AnsibleError) as err:
            self.call_lookup(*terms, variables=self.cluster_vars)

        self.assertEqual(str(err.exception), f"not enough arguments to set config ({len(terms)} of 3)")

    def test_job_id_is_read_before_terms_check_fail(self) -> None:
        # `job` is read first, so absence of it "shadows" arguments check with a bare KeyError
        with self.assertRaises(KeyError):
            self.call_lookup(variables={})

    def test_extra_terms_are_ignored_success(self) -> None:
        result = self.call_lookup(
            "cluster", "plain_s", "changed", "ignored", "also ignored", variables=self.cluster_vars
        )

        self.assertEqual(result, PluginResult("changed", True))
        self.assertEqual(self.get_config(self.cluster)["plain_s"], "changed")

    def test_unknown_kwargs_are_ignored_success(self) -> None:
        result = self.call_lookup(
            "cluster", "plain_s", "changed", variables=self.cluster_vars, whatever="ignored", another=42
        )

        self.assertEqual(result, PluginResult("changed", True))

    @parametrize(
        ("key", "value", "config_path"),
        [
            param("plain_s", "changed", ("plain_s",), id="plain_key"),
            param("g1/plain_s", "changed", ("g1", "plain_s"), id="key_with_subkey"),
        ],
    )
    def test_key_is_split_by_slash_success(self, key: str, value: Any, config_path: tuple[str, ...]) -> None:
        result = self.call_lookup("cluster", key, value, variables=self.cluster_vars)

        self.assertEqual(result, PluginResult(value, True))

        config = self.get_config(self.cluster)
        for part in config_path:
            config = config[part]

        self.assertEqual(config, value)

    def test_group_name_as_key_replaces_whole_group_success(self) -> None:
        # group has its own `PrototypeConfig` record with empty subname, so it is writable "as is"
        new_group = {"plain_s": "brand new", "plain_i": 100}

        result = self.call_lookup("cluster", "g1", new_group, variables=self.cluster_vars)

        self.assertEqual(result, PluginResult(new_group, True))
        self.assertEqual(self.get_config(self.cluster)["g1"], new_group)

    @parametrize(
        "key",
        [
            param("g1/plain_s/plain_i", id="third_slash_part_ignored"),
        ],
    )
    def test_extra_key_parts_are_ignored_success(self, key: str) -> None:
        result = self.call_lookup("cluster", key, "changed", variables=self.cluster_vars)

        self.assertEqual(result, PluginResult("changed", True))
        self.assertEqual(self.get_config(self.cluster)["g1"]["plain_s"], "changed")

    @parametrize(
        "string_type",
        [
            param(AnsibleUnsafeText, id="unsafe_text"),
            param(AnsibleUnicode, id="unicode"),
        ],
    )
    def test_ansible_string_types_success(self, string_type: type) -> None:
        result = self.call_lookup(
            string_type("cluster"), string_type("g1/plain_s"), string_type("changed"), variables=self.cluster_vars
        )

        self.assertEqual(result, PluginResult("changed", True))
        self.assertEqual(self.get_config(self.cluster)["g1"]["plain_s"], "changed")

    def test_unknown_parameter_fail(self) -> None:
        with self.assertRaises(AnsibleError) as err:
            self.call_lookup("cluster", "no_such_param", "changed", variables=self.cluster_vars)

        self.assertEqual(str(err.exception), "Config parameter 'no_such_param' does not exist")

    def test_unknown_subparameter_fail(self) -> None:
        with self.assertRaises(AnsibleError) as err:
            self.call_lookup("cluster", "g1/no_such_param", "changed", variables=self.cluster_vars)

        self.assertEqual(str(err.exception), "Config parameter 'g1/no_such_param' does not exist")

    # Target detection

    def test_cluster_target_success(self) -> None:
        target = detect_target(terms=["cluster"], variables=self.cluster_vars, kwargs={})

        self.assertIsInstance(target, Cluster)
        self.assertEqual(target.pk, self.cluster.pk)

    def test_provider_target_success(self) -> None:
        target = detect_target(terms=["provider"], variables=self.provider_vars, kwargs={})

        self.assertIsInstance(target, Provider)
        self.assertEqual(target.pk, self.provider.pk)

    def test_host_target_success(self) -> None:
        variables = self.build_variables(job_id=self.provider_job_id, host=self.host)

        target = detect_target(terms=["host"], variables=variables, kwargs={})

        self.assertIsInstance(target, Host)
        self.assertEqual(target.pk, self.host.pk)

    def test_service_target_by_name_success(self) -> None:
        variables = self.build_variables(job_id=self.cluster_job_id, cluster=True)

        target = detect_target(terms=["service"], variables=variables, kwargs={"service_name": self.service_2.name})

        self.assertIsInstance(target, Service)
        self.assertEqual(target.pk, self.service_2.pk)

    def test_service_target_by_job_service_id_success(self) -> None:
        variables = self.build_variables(job_id=self.cluster_job_id, cluster=True, service_id=self.service_1.pk)

        target = detect_target(terms=["service"], variables=variables, kwargs={})

        self.assertIsInstance(target, Service)
        self.assertEqual(target.pk, self.service_1.pk)

    def test_service_name_wins_over_job_service_id_success(self) -> None:
        variables = self.build_variables(job_id=self.cluster_job_id, cluster=True, service_id=self.service_1.pk)

        target = detect_target(terms=["service"], variables=variables, kwargs={"service_name": self.service_2.name})

        self.assertEqual(target.pk, self.service_2.pk)

    @parametrize(
        ("type_", "message"),
        [
            param("cluster", "there is no cluster in hostvars", id="cluster"),
            param("service", "there is no cluster in hostvars", id="service"),
            param("provider", "there is no host provider in hostvars", id="provider"),
            param("host", "there is no adcm_hostid in hostvars", id="host"),
        ],
    )
    def test_missing_variable_fail(self, type_: str, message: str) -> None:
        variables = self.build_variables(job_id=self.cluster_job_id)

        with self.assertRaises(AnsibleError) as err:
            detect_target(terms=[type_], variables=variables, kwargs={})

        self.assertEqual(str(err.exception), message)

    def test_service_without_name_and_job_service_id_fail(self) -> None:
        with self.assertRaises(AnsibleError) as err:
            detect_target(terms=["service"], variables=self.cluster_vars, kwargs={})

        self.assertEqual(str(err.exception), "no service_id in job or service_name and service_version in params")

    @parametrize(
        "type_",
        [
            param("component", id="component"),
            param("adcm", id="adcm"),
            param("", id="empty"),
            param("Cluster", id="unexpected_case"),
        ],
    )
    def test_unsupported_type_fail(self, type_: str) -> None:
        with self.assertRaises(AnsibleError) as err:
            detect_target(terms=[type_], variables=self.cluster_vars, kwargs={})

        self.assertEqual(str(err.exception), f"unknown object type: {type_}")

    @parametrize(
        ("type_", "variable", "error_code"),
        [
            param("cluster", "cluster", "CLUSTER_NOT_FOUND", id="cluster"),
            param("provider", "provider", "PROVIDER_NOT_FOUND", id="provider"),
        ],
    )
    def test_nonexistent_object_fail(self, type_: str, variable: str, error_code: str) -> None:
        variables = self.build_variables(job_id=self.cluster_job_id)
        variables[variable] = {"id": 1000}

        with self.assertRaises(AdcmEx) as err:
            detect_target(terms=[type_], variables=variables, kwargs={})

        self.assertEqual(err.exception.code, error_code)

    def test_nonexistent_host_fail(self) -> None:
        variables = self.build_variables(job_id=self.provider_job_id)
        variables["adcm_hostid"] = 1000

        with self.assertRaises(AdcmEx) as err:
            detect_target(terms=["host"], variables=variables, kwargs={})

        self.assertEqual(err.exception.code, "HOST_NOT_FOUND")

    def test_nonexistent_service_name_fail(self) -> None:
        with self.assertRaises(AdcmEx) as err:
            detect_target(terms=["service"], variables=self.cluster_vars, kwargs={"service_name": "no_such_service"})

        self.assertEqual(err.exception.code, "PROTOTYPE_NOT_FOUND")

    def test_service_from_another_cluster_fail(self) -> None:
        another_cluster = self.uc.add_cluster(bundle=self.cluster_bundle, name="Another Cluster")
        variables = self.build_variables(job_id=self.cluster_job_id, service_id=self.service_1.pk)
        variables["cluster"] = {"id": another_cluster.pk}

        with self.assertRaises(AdcmEx) as err:
            detect_target(terms=["service"], variables=variables, kwargs={})

        self.assertEqual(err.exception.code, "CLUSTER_SERVICE_NOT_FOUND")

    def test_target_is_not_checked_against_job_owner_success(self) -> None:
        # unlike `ADCMConfigPluginExecutor`, lookup allows changing any object present in variables:
        # here provider-owned job changes cluster's config
        variables = self.build_variables(job_id=self.provider_job_id, cluster=True)

        target = detect_target(terms=["cluster"], variables=variables, kwargs={})

        self.assertEqual(target.pk, self.cluster.pk)

    # Config change itself

    @parametrize(
        ("type_", "key", "value"),
        [
            param("cluster", "plain_s", "changed", id="cluster"),
            param("service", "plain_s", "changed", id="service_by_name"),
            param("provider", "plain_s", "changed", id="provider"),
            param("host", "plain_s", "changed", id="host"),
        ],
    )
    def test_change_for_each_target_success(self, type_: str, key: str, value: Any) -> None:
        match type_:
            case "cluster":
                variables, target = self.cluster_vars, self.cluster
                kwargs = {}
            case "service":
                variables, target = self.cluster_vars, self.service_1
                kwargs = {"service_name": self.service_1.name}
            case "provider":
                variables, target = self.provider_vars, self.provider
                kwargs = {}
            case _:
                variables = self.build_variables(job_id=self.provider_job_id, host=self.host)
                target, kwargs = self.host, {}

        result = self.call_lookup(type_, key, value, variables=variables, **kwargs)

        self.assertEqual(result, PluginResult(value, True))
        self.assertEqual(self.get_config(target)[key], value)

    @parametrize(
        ("key", "value", "expected_stored"),
        [
            param("plain_i", "42", 42, id="integer_from_string"),
            param("plain_i", 42, 42, id="integer_from_int"),
            param("plain_f", "4.2", 4.2, id="float_from_string"),
            param("plain_f", 4, 4.0, id="float_from_int"),
            param("plain_o", 2, 2, id="option_known_value"),
            param("plain_o", "2", 2, id="option_numeric_string"),
        ],
    )
    def test_value_is_casted_to_parameter_type_success(self, key: str, value: Any, expected_stored: Any) -> None:
        result = self.call_lookup("cluster", key, value, variables=self.cluster_vars)

        # returned value is the raw input, not the casted one
        self.assertEqual(result, PluginResult(value, True))

        stored = self.get_config(self.cluster)[key]
        self.assertEqual(stored, expected_stored)
        self.assertIsInstance(stored, type(expected_stored))

    @parametrize(
        ("key", "value", "message_start"),
        [
            param("plain_s", 42, 'Value ("42") of config key "plain_s" should be string', id="int_for_string"),
            param("plain_b", "yes", 'Value ("yes") of config key "plain_b" should be boolean', id="string_for_boolean"),
        ],
    )
    def test_type_not_covered_by_cast_is_rejected_on_save_fail(self, key: str, value: Any, message_start: str) -> None:
        # `cast_to_type` handles only integer/float/option, the rest is validated by config processing
        #
        # BEHAVIOR CHANGED SINCE 2.12: only the error text, the lookup itself is intact.
        # In 2.12 the key was rendered as `"plain_s/"` (name with trailing slash for a top-level parameter);
        # since ADCM-7268 parameter's display name is used instead, so it is `"plain_s"`.
        with self.assertRaises(AdcmEx) as err:
            self.call_lookup("cluster", key, value, variables=self.cluster_vars)

        self.assertEqual(err.exception.code, "CONFIG_VALUE_ERROR")
        self.assertIn(message_start, err.exception.msg)

    def test_uncastable_integer_fail(self) -> None:
        # not an `AnsibleError`: casting errors are not handled at all
        with self.assertRaises(ValueError):
            self.call_lookup("cluster", "plain_i", "not a number", variables=self.cluster_vars)

    def test_unknown_option_value_fail(self) -> None:
        with self.assertRaises(AdcmEx) as err:
            self.call_lookup("cluster", "plain_o", "third", variables=self.cluster_vars)

        self.assertEqual(err.exception.code, "CONFIG_OPTION_ERROR")

    def test_same_value_is_not_changed_success(self) -> None:
        config_logs_before = self.get_config_log_amount(self.cluster)

        result = self.call_lookup("cluster", "plain_s", "initial", variables=self.cluster_vars)

        # note the asymmetry: unchanged call returns `{key: value}` dict, changed one returns bare value
        self.assertEqual(result, PluginResult({"plain_s": "initial"}, False))
        self.assertEqual(self.get_config_log_amount(self.cluster), config_logs_before)

    def test_same_value_after_cast_is_not_changed_success(self) -> None:
        result = self.call_lookup("cluster", "plain_i", "3", variables=self.cluster_vars)

        self.assertEqual(result, PluginResult({"plain_i": "3"}, False))

    def test_secret_value_is_always_changed_success(self) -> None:
        # config stores encrypted value, it is compared against plain one, so change is always detected
        config_logs_before = self.get_config_log_amount(self.cluster)

        result = self.call_lookup("cluster", "secret", "initial secret", variables=self.cluster_vars)

        self.assertEqual(result, PluginResult("initial secret", True))
        self.assertEqual(self.get_config_log_amount(self.cluster), config_logs_before + 1)

    def test_change_creates_new_config_log_success(self) -> None:
        config_logs_before = self.get_config_log_amount(self.cluster)

        self.call_lookup("cluster", "plain_s", "changed", variables=self.cluster_vars)

        self.assertEqual(self.get_config_log_amount(self.cluster), config_logs_before + 1)

        self.cluster.refresh_from_db(fields=["config"])
        config_log = ConfigLog.objects.get(id=self.cluster.config.current)
        self.assertEqual(config_log.description, "ansible update")

    def test_other_parameters_are_kept_success(self) -> None:
        before = copy.deepcopy(self.get_config(self.cluster))

        self.call_lookup("cluster", "plain_s", "changed", variables=self.cluster_vars)

        after = self.get_config(self.cluster)
        before["plain_s"] = "changed"

        self.assertDictEqual(after, before)

    def test_subsequent_calls_success(self) -> None:
        first = self.call_lookup("cluster", "plain_s", "first", variables=self.cluster_vars)
        second = self.call_lookup("cluster", "plain_s", "second", variables=self.cluster_vars)
        third = self.call_lookup("cluster", "plain_s", "second", variables=self.cluster_vars)

        self.assertEqual(first, PluginResult("first", True))
        self.assertEqual(second, PluginResult("second", True))
        self.assertEqual(third, PluginResult({"plain_s": "second"}, False))
        self.assertEqual(self.get_config(self.cluster)["plain_s"], "second")

    # Ansible-facing part of the plugin

    def test_run_returns_list_with_value_success(self) -> None:
        result = LookupModule().run(["cluster", "plain_s", "changed"], variables=self.cluster_vars)

        self.assertEqual(result, ["changed"])

    def test_run_returns_list_with_dict_when_not_changed_success(self) -> None:
        result = LookupModule().run(["cluster", "plain_s", "initial"], variables=self.cluster_vars)

        self.assertEqual(result, [{"plain_s": "initial"}])

    def test_run_passes_kwargs_success(self) -> None:
        result = LookupModule().run(
            ["service", "plain_s", "changed"], variables=self.cluster_vars, service_name=self.service_2.name
        )

        self.assertEqual(result, ["changed"])
        self.assertEqual(self.get_config(self.service_2)["plain_s"], "changed")
