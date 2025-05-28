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
from typing import Iterable

from cm.converters import orm_object_to_core_type
from cm.models import (
    Action,
    ADCMEntity,
    Bundle,
    Cluster,
    Component,
    ConcernCause,
    ConcernItem,
    ConcernType,
    Host,
    JobLog,
    ObjectType,
    Prototype,
    PrototypeImport,
    Provider,
    Service,
)
from cm.services.concern.flags import BuiltInFlag, lower_flag
from cm.services.concern.messages import ConcernMessage
from cm.tests.mocks.task_runner import RunTaskMock
from core.cluster.types import ObjectMaintenanceModeState as MM  # noqa: N814
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.tests.base import BaseAPITestCase


class TestConcernsResponse(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle_dir = self.test_bundles_dir / "cluster_with_required_service"
        self.required_service_bundle = self.add_bundle(source_dir=bundle_dir)

        bundle_dir = self.test_bundles_dir / "cluster_with_required_config_field"
        self.required_config_bundle = self.add_bundle(source_dir=bundle_dir)

        bundle_dir = self.test_bundles_dir / "cluster_with_required_import"
        self.required_import_bundle = self.add_bundle(source_dir=bundle_dir)

        bundle_dir = self.test_bundles_dir / "cluster_with_required_hc"
        self.required_hc_bundle = self.add_bundle(source_dir=bundle_dir)

        bundle_dir = self.test_bundles_dir / "cluster_with_allowed_flags"
        self.config_flag_bundle = self.add_bundle(source_dir=bundle_dir)

        bundle_dir = self.test_bundles_dir / "cluster_with_service_requirements"
        self.service_requirements_bundle = self.add_bundle(source_dir=bundle_dir)

        bundle_dir = self.test_bundles_dir / "cluster_concerns_with_dependencies"
        self.complex_dependencies = self.add_bundle(source_dir=bundle_dir)

        bundle_dir = self.test_bundles_dir / "provider_outdated_config"
        self.provider_changed_state = self.add_bundle(source_dir=bundle_dir)

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

    def test_required_service_concern(self):
        cluster = self.add_cluster(bundle=self.required_service_bundle, name="required_service_cluster")
        expected_concern_reason = {
            "message": ConcernMessage.REQUIRED_SERVICE_ISSUE.template.message,
            "placeholder": {
                "source": {"type": "cluster_services", "name": cluster.name, "params": {"clusterId": cluster.pk}},
                "target": {
                    "params": {
                        "prototypeId": Prototype.objects.get(
                            type=ObjectType.SERVICE, name="service_required", required=True
                        ).pk
                    },
                    "type": "prototype",
                    "name": "service_required",
                },
            },
        }

        response = self.client.v2[cluster].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data["concerns"]), 1)
        concern, *_ = data["concerns"]
        self.assertEqual(concern["type"], "issue")
        self.assertDictEqual(concern["reason"], expected_concern_reason)

    def test_required_config_concern(self):
        cluster = self.add_cluster(bundle=self.required_config_bundle, name="required_config_cluster")
        expected_concern_reason = {
            "message": ConcernMessage.CONFIG_ISSUE.template.message,
            "placeholder": {
                "source": {"name": cluster.name, "params": {"clusterId": cluster.pk}, "type": "cluster_config"}
            },
        }

        response = self.client.v2[cluster].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data["concerns"]), 1)
        concern, *_ = data["concerns"]
        self.assertEqual(concern["type"], "issue")
        self.assertDictEqual(concern["reason"], expected_concern_reason)

    def test_required_import_concern(self):
        cluster = self.add_cluster(bundle=self.required_import_bundle, name="required_import_cluster")
        expected_concern_reason = {
            "message": ConcernMessage.REQUIRED_IMPORT_ISSUE.template.message,
            "placeholder": {
                "source": {"name": cluster.name, "params": {"clusterId": cluster.pk}, "type": "cluster_import"}
            },
        }

        response = self.client.v2[cluster].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertDictEqual(response.json()["concerns"][0]["reason"], expected_concern_reason)

    def test_adcm_6354_hostprovider_action_concern_locks_all_related_clusters_success(self):
        cluster_1 = self.add_cluster(bundle=self.complex_dependencies, name="cluster_with_dependencies_1")
        cluster_2 = self.add_cluster(bundle=self.complex_dependencies, name="cluster_with_dependencies_2")
        cluster_3 = self.add_cluster(bundle=self.complex_dependencies, name="cluster_with_dependencies_3")
        second_provider = self.add_provider(Bundle.objects.get(name="provider"), "Second Provider")

        self.add_services_to_cluster(service_names=["first_service"], cluster=cluster_1)
        self.add_services_to_cluster(service_names=["first_service"], cluster=cluster_2)
        self.add_services_to_cluster(service_names=["first_service"], cluster=cluster_3)

        hosts = []

        for host_n in range(1, 4):
            cluster = cluster_1 if host_n % 2 == 0 else cluster_2
            hosts.append(self.add_host(provider=self.provider, fqdn=f"host_{host_n}", cluster=cluster))
            hostcomponent_entry = (
                Host.objects.get(fqdn=f"host_{host_n}"),
                Component.objects.get(cluster=cluster, prototype__name="first_component"),
            )
            self.set_hostcomponent(cluster=cluster, entries=[hostcomponent_entry])

        host_from_second_provider = self.add_host(provider=second_provider, fqdn="host_5", cluster=cluster_3)
        hostcomponent_entry = (
            host_from_second_provider,
            Component.objects.get(cluster=cluster_3, prototype__name="first_component"),
        )
        self.set_hostcomponent(cluster=cluster_3, entries=[hostcomponent_entry])

        objects_to_be_locked_by_action = sorted(
            [(cluster.pk, cluster.prototype_id) for cluster in [cluster_1, cluster_2]]
            + list(
                Service.objects.filter(prototype__name="first_service")
                .exclude(cluster__name="cluster_with_dependencies_3")
                .values_list("pk", "prototype_id")
            )
            + list(
                Component.objects.filter(prototype__name="first_component")
                .exclude(cluster__name="cluster_with_dependencies_3")
                .values_list("pk", "prototype_id")
            )
            + [(host.pk, host.prototype_id) for host in hosts]
            + [(self.provider.pk, self.provider.prototype_id)]
        )

        free_objects = sorted(
            [(cluster.pk, cluster.prototype_id) for cluster in [cluster_3]]
            + list(
                Service.objects.filter(
                    prototype__name="first_service", cluster__name="cluster_with_dependencies_3"
                ).values_list("pk", "prototype_id")
            )
            + list(
                Component.objects.filter(
                    prototype__name="first_component", cluster__name="cluster_with_dependencies_3"
                ).values_list("pk", "prototype_id")
            )
            + [(host_from_second_provider.pk, host_from_second_provider.prototype_id)]
            + [(second_provider.pk, second_provider.prototype_id)]
        )

        def run_action(_object, object_action) -> list[tuple[int, int]]:
            response = self.client.v2[_object, "actions", object_action, "run"].post()
            self.assertEqual(response.status_code, HTTP_200_OK)

            concern = ConcernItem.objects.filter(name="job_lock").first()
            related_objects = sorted([(o.id, o.prototype_id) for o in concern.related_objects])
            concern.delete()

            return related_objects

        provider_action = Action.objects.filter(prototype=self.provider.prototype).first()
        related_objects = run_action(self.provider, provider_action)
        self.assertEqual(related_objects, objects_to_be_locked_by_action)

        for obj in free_objects:
            self.assertNotIn(obj, related_objects)

    def test_adcm_6275_concern_propagation_success(self):
        cluster = self.add_cluster(bundle=self.complex_dependencies, name="cluster_with_dependencies")
        self.add_services_to_cluster(
            service_names=["first_service", "second_service", "third_service"], cluster=cluster
        )

        components = Component.objects.filter(cluster=cluster)

        hosts = []
        for host_n in range(1, 4):
            hosts.append(self.add_host(provider=self.provider, fqdn=f"host_{host_n}", cluster=cluster))

        hostcomponent_entries = []
        for i, component in enumerate(components.exclude(prototype__name="single_component")):
            if i % 2 == 0:
                hostcomponent_entries.append((hosts[0], component))
            else:
                hostcomponent_entries.append((hosts[1], component))

        hostcomponent_entries.append(
            (hosts[2], Component.objects.get(cluster=cluster, prototype__name="single_component"))
        )

        self.set_hostcomponent(cluster=cluster, entries=hostcomponent_entries)

        objects_to_be_locked_by_action = sorted(
            [(cluster.pk, cluster.prototype_id)]
            + list(Service.objects.exclude(prototype__name="third_service").values_list("pk", "prototype_id"))
            + list(Component.objects.filter(hostcomponent__host=hosts[0]).values_list("pk", "prototype_id"))
            + [(hosts[0].pk, hosts[0].prototype_id)]
        )

        def run_action(_object, object_action) -> list[tuple[int, int]]:
            response = self.client.v2[_object, "actions", object_action, "run"].post()
            self.assertEqual(response.status_code, HTTP_200_OK)

            concern = ConcernItem.objects.filter(name="job_lock").first()
            related_objects = sorted([(o.id, o.prototype_id) for o in concern.related_objects])
            concern.delete()

            return related_objects

        with self.subTest("Action is run on component"):
            component = components.get(prototype__name="first_component", service__prototype__name="first_service")
            component_action = Action.objects.get(name="action", prototype=component.prototype)

            related_objects = run_action(component, component_action)

            self.assertListEqual(related_objects, objects_to_be_locked_by_action)

        with self.subTest("Action is run on service"):
            service = Service.objects.get(prototype__name="first_service")
            service_action = Action.objects.get(name="action", prototype=service.prototype)

            related_objects = run_action(service, service_action)

            self.assertListEqual(
                related_objects,
                sorted(
                    objects_to_be_locked_by_action
                    + list(Component.objects.filter(hostcomponent__host=hosts[1]).values_list("pk", "prototype_id"))
                    + [(hosts[1].pk, hosts[1].prototype_id)]
                ),
            )

        with self.subTest("Action is run on host"):
            host = Host.objects.get(fqdn="host_1")
            host_action = Action.objects.get(prototype=host.prototype)

            related_objects = run_action(host, host_action)

            self.assertListEqual(related_objects, objects_to_be_locked_by_action)

    def test_required_hc_concern(self):
        cluster = self.add_cluster(bundle=self.required_hc_bundle, name="required_hc_cluster")
        self.add_services_to_cluster(service_names=["service_1"], cluster=cluster)
        expected_concern_reason = {
            "message": ConcernMessage.HOST_COMPONENT_ISSUE.template.message,
            "placeholder": {
                "source": {"name": cluster.name, "params": {"clusterId": cluster.pk}, "type": "cluster_mapping"}
            },
        }

        response = self.client.v2[cluster].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertDictEqual(response.json()["concerns"][0]["reason"], expected_concern_reason)

    def test_outdated_config_flag(self):
        cluster = self.add_cluster(bundle=self.config_flag_bundle, name="config_flag_cluster")
        expected_concern_reason = {
            "message": f"{ConcernMessage.FLAG.template.message}outdated config",
            "placeholder": {"source": {"name": cluster.name, "params": {"clusterId": cluster.pk}, "type": "cluster"}},
        }

        response = self.client.v2[cluster, "configs"].post(
            data={"config": {"string": "new_string 2"}, "adcmMeta": {}, "description": ""},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = self.client.v2[cluster].get()
        self.assertEqual(response.status_code, HTTP_200_OK)

        with self.subTest("Absent on state = 'created'"):
            data = response.json()
            self.assertEqual(len(data["concerns"]), 0)

        cluster.state = "notcreated"
        cluster.save(update_fields=["state"])

        response = self.client.v2[cluster, "configs"].post(
            data={"config": {"string": "new_string"}, "adcmMeta": {}, "description": ""},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = self.client.v2[cluster].get()
        self.assertEqual(response.status_code, HTTP_200_OK)

        with self.subTest("Present on another state"):
            data = response.json()
            self.assertEqual(len(data["concerns"]), 1)
            concern, *_ = data["concerns"]
            self.assertEqual(concern["type"], "flag")
            self.assertDictEqual(concern["reason"], expected_concern_reason)

    def test_raise_outdated_config_if_configs_differ_only_success(self):
        cluster = self.cluster_1
        cluster.state = "notcreated"
        cluster.save(update_fields=["state"])
        initial_config = {
            "activatable_group": {"integer": 10},
            "boolean": True,
            "group": {"float": 0.1},
            "list": ["value1", "value2", "value3"],
            "variant_not_strict": "value1",
        }
        initial_attrs = {"/activatable_group": {"isActive": True}}

        with self.subTest("No outdated flag - configs are same"):
            response = self.client.v2[cluster, "configs"].post(
                data={"config": initial_config, "adcmMeta": initial_attrs, "description": "init"},
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)

            concerns = ConcernItem.objects.filter(owner_id=cluster.pk, owner_type=cluster.content_type)
            self.assertEqual(len(concerns), 0)

        with self.subTest("Outdated flag - new config content differs"):
            initial_config["boolean"] = False
            response = self.client.v2[cluster, "configs"].post(
                data={"config": initial_config, "adcmMeta": initial_attrs, "description": "init"},
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)

            concerns = ConcernItem.objects.filter(owner_id=cluster.pk, owner_type=cluster.content_type)
            self.assertEqual(len(concerns), 1)
            self.assertEqual(concerns.first().cause, "config")

        lower_flag(
            BuiltInFlag.ADCM_OUTDATED_CONFIG.value.name,
            on_objects=[CoreObjectDescriptor(id=cluster.id, type=ADCMCoreType.CLUSTER)],
        )

        with self.subTest("Outdated flag - new config adcm Meta differs"):
            initial_attrs = {"/activatable_group": {"isActive": False}}
            response = self.client.v2[cluster, "configs"].post(
                data={"config": initial_config, "adcmMeta": initial_attrs},
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)

            concerns = ConcernItem.objects.filter(owner_id=cluster.pk, owner_type=cluster.content_type)
            self.assertEqual(len(concerns), 1)
            self.assertEqual(concerns.first().cause, "config")

        with self.subTest("Adcm-6562 raise outdated_config for provider"):
            provider = self.add_provider(bundle=self.provider_changed_state, name="provider_outdated_state")
            provider.state = "notcreated"
            provider.save(update_fields=["state"])

            response = self.client.v2[provider, "configs"].post(
                data={"config": {"int_param": 13, "string_param": "new_string"}, "adcmMeta": {}, "description": "init"},
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)

            concerns = ConcernItem.objects.filter(owner_id=provider.pk, owner_type=provider.content_type)
            self.assertEqual(len(concerns), 1)
            self.assertEqual(concerns.first().cause, "config")

    def test_service_requirements(self):
        cluster = self.add_cluster(bundle=self.service_requirements_bundle, name="service_requirements_cluster")
        service = self.add_services_to_cluster(service_names=["service_1"], cluster=cluster).get()
        expected_concern_reason = {
            "message": ConcernMessage.UNSATISFIED_REQUIREMENT_ISSUE.template.message,
            "placeholder": {
                "source": {
                    "name": service.name,
                    "params": {"clusterId": cluster.pk, "serviceId": service.pk},
                    "type": "cluster_services",
                },
                "target": {
                    "name": "some_other_service",
                    "params": {
                        "prototypeId": Prototype.objects.get(type=ObjectType.SERVICE, name="some_other_service").pk
                    },
                    "type": "prototype",
                },
            },
        }

        response = self.client.v2[service].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertDictEqual(response.json()["concerns"][0]["reason"], expected_concern_reason)

    def test_job_concern(self):
        action = Action.objects.filter(prototype=self.cluster_1.prototype).first()

        with RunTaskMock():
            response = self.client.v2[self.cluster_1, "actions", action, "run"].post(
                data={"configuration": None, "isVerbose": True, "hostComponentMap": []},
            )

            self.assertEqual(response.status_code, HTTP_200_OK)

            expected_concern_reason = {
                "message": ConcernMessage.LOCKED_BY_JOB.template.message,
                "placeholder": {
                    "job": {
                        "type": "job",
                        "name": "action",
                        "params": {"taskId": JobLog.objects.get(name=action.name).pk},
                    },
                    "target": {"type": "cluster", "name": "cluster_1", "params": {"clusterId": self.cluster_1.pk}},
                },
            }

            response = self.client.v2[self.cluster_1].get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(len(response.json()["concerns"]), 1)
            self.assertDictEqual(response.json()["concerns"][0]["reason"], expected_concern_reason)

    def test_permissions_to_delete_concern_item(self):
        cluster = self.cluster_1
        provider = self.add_provider(bundle=self.provider_changed_state, name="provider_outdated_state")

        service, service_2 = self.add_services_to_cluster(service_names=["service_1", "service_2"], cluster=cluster)

        component = Component.objects.filter(service__prototype__name="service_1").first()

        component_initial_config = component.config.configlog_set.last().config

        initial_attrs = {"/activatable_group": {"isActive": True}}

        for obj in [cluster, service, service_2, component, provider]:
            obj.state = "notcreated"
            obj.save(update_fields=["state"])

        self.client.login(**self.test_user_credentials)

        with self.subTest("Outdated flag - No permissions for concern owner"):
            with self.grant_permissions(to=self.test_user, on=component, role_name="Edit component configurations"):
                component_initial_config["group"]["file"] = "test"
                response = self.client.v2[component, "configs"].post(
                    data={"config": component_initial_config, "adcmMeta": initial_attrs, "description": "init"},
                )
                self.assertEqual(response.status_code, HTTP_201_CREATED)

                concerns = component.concerns.all()
                self.assertEqual(len(concerns), 1)
                self.assertEqual(concerns.first().cause, "config")

            with self.grant_permissions(to=self.test_user, on=service_2, role_name="Service Administrator"):
                response = self.client.v2[concerns.first()].delete()
                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

                concerns = component.concerns.all()
                self.assertEqual(len(concerns), 1)

        with self.subTest("Outdated flag - No remove concern permissions"):
            with self.grant_permissions(to=self.test_user, on=component, role_name="Edit component configurations"):
                component_initial_config["group"]["file"] = "test2"
                response = self.client.v2[component, "configs"].post(
                    data={"config": component_initial_config, "adcmMeta": initial_attrs, "description": "init"},
                )
                self.assertEqual(response.status_code, HTTP_201_CREATED)

                concerns = component.concerns.all()
                self.assertEqual(len(concerns), 1)
                self.assertEqual(concerns.first().cause, "config")

                response = self.client.v2[concerns.last()].delete()
                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

                concerns = component.concerns.all()
                self.assertEqual(len(concerns), 1)

        with self.subTest("Outdated flag - Cluster Administrator permissions"):
            with self.grant_permissions(to=self.test_user, on=cluster, role_name="Cluster Administrator"):
                component_initial_config["group"]["file"] = "test3"
                response = self.client.v2[component, "configs"].post(
                    data={"config": component_initial_config, "adcmMeta": initial_attrs, "description": "init"},
                )
                self.assertEqual(response.status_code, HTTP_201_CREATED)

                concerns = component.concerns.all()
                self.assertEqual(len(concerns), 1)
                self.assertEqual(concerns.first().cause, "config")

                response = self.client.v2[concerns.last()].delete()
                self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

                concerns = component.concerns.all()
                self.assertEqual(len(concerns), 0)

        with self.subTest("Outdated flag - Service Administrator permissions"):
            with self.grant_permissions(to=self.test_user, on=service, role_name="Service Administrator"):
                component_initial_config["group"]["file"] = "test4"
                response = self.client.v2[component, "configs"].post(
                    data={"config": component_initial_config, "adcmMeta": initial_attrs, "description": "init"},
                )
                self.assertEqual(response.status_code, HTTP_201_CREATED)

                concerns = component.concerns.all()
                self.assertEqual(len(concerns), 1)
                self.assertEqual(concerns.first().cause, "config")

                response = self.client.v2[concerns.last()].delete()
                self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

                concerns = component.concerns.all()
                self.assertEqual(len(concerns), 0)

        with self.subTest("Outdated flag - Provider Administrator permissions"):
            with self.grant_permissions(to=self.test_user, on=provider, role_name="Provider Administrator"):
                response = self.client.v2[provider, "configs"].post(
                    data={
                        "config": {"string_param": "new_string", "int_param": 2},
                        "adcmMeta": {},
                        "description": "init",
                    },
                )
                self.assertEqual(response.status_code, HTTP_201_CREATED)

                concerns = provider.concerns.all()
                self.assertEqual(len(concerns), 1)
                self.assertEqual(concerns.first().cause, "config")

                response = self.client.v2[concerns.last()].delete()
                self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

                concerns = provider.concerns.all()
                self.assertEqual(len(concerns), 0)

        with self.subTest("Outdated flag - Concern couldn't be deleted due to action"):
            with self.grant_permissions(to=self.test_user, on=cluster, role_name="Cluster Administrator"):
                component_initial_config["group"]["file"] = "test5"
                response = self.client.v2[component, "configs"].post(
                    data={"config": component_initial_config, "adcmMeta": initial_attrs, "description": "init"},
                )
                self.assertEqual(response.status_code, HTTP_201_CREATED)

                concerns = component.concerns.all()
                self.assertEqual(len(concerns), 1)
                self.assertEqual(concerns.first().cause, "config")

                action = Action.objects.get(name="action_1_comp_1", prototype=component.prototype)
                response = self.client.v2[component, "actions", action, "run"].post()
                self.assertEqual(response.status_code, HTTP_200_OK)

                response = self.client.v2[concerns.last()].delete()
                self.assertEqual(response.status_code, HTTP_409_CONFLICT)

                concerns = component.concerns.all()
                self.assertEqual(len(concerns), 2)


class TestConcernsLogic(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle_dir = self.test_bundles_dir / "cluster_with_required_import"
        self.required_import_bundle = self.add_bundle(source_dir=bundle_dir)

        bundle_dir = self.test_bundles_dir / "cluster_with_service_requirements"
        self.service_requirements_bundle = self.add_bundle(source_dir=bundle_dir)

        bundle_dir = self.test_bundles_dir / "hc_mapping_constraints"
        self.hc_mapping_constraints_bundle = self.add_bundle(source_dir=bundle_dir)

        bundle_dir = self.test_bundles_dir / "service_add_concerns"
        self.service_add_concerns_bundle = self.add_bundle(source_dir=bundle_dir)

        bundle_dir = self.test_bundles_dir / "provider_no_config"
        self.provider_no_config_bundle = self.add_bundle(source_dir=bundle_dir)

    def _check_concerns(self, object_: Cluster | Service | Component, expected_concerns: list[dict]):
        object_concerns = object_.concerns.all()
        self.assertEqual(object_concerns.count(), len(expected_concerns))

        for expected_concern in expected_concerns:
            target_concern = object_concerns.filter(
                owner_id=expected_concern["owner_id"],
                owner_type=expected_concern["owner_type"],
                cause=expected_concern["cause"],
                name=expected_concern["name"],
                type="issue",
            )
            self.assertEqual(target_concern.count(), 1)

    def test_import_concern_resolved_after_saving_import(self):
        import_cluster = self.add_cluster(bundle=self.required_import_bundle, name="required_import_cluster")
        unused_import_cluster = self.add_cluster(bundle=self.required_import_bundle, name="unused_import_cluster")
        export_cluster = self.cluster_1

        response = self.client.v2[import_cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertEqual(import_cluster.concerns.count(), 1)

        response = self.client.v2[unused_import_cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertEqual(import_cluster.concerns.count(), 1)

        self.client.v2[import_cluster, "imports"].post(
            data=[{"source": {"id": export_cluster.pk, "type": ObjectType.CLUSTER}}],
        )

        response = self.client.v2[import_cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 0)
        self.assertEqual(import_cluster.concerns.count(), 0)

        response = self.client.v2[unused_import_cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertEqual(unused_import_cluster.concerns.count(), 1)

    def test_non_required_import_do_not_raises_concern(self):
        self.assertGreater(PrototypeImport.objects.filter(prototype=self.cluster_2.prototype).count(), 0)

        response = self.client.v2[self.cluster_2].get()
        self.assertEqual(len(response.json()["concerns"]), 0)
        self.assertEqual(self.cluster_2.concerns.count(), 0)

    def test_concern_owner_cluster(self):
        import_cluster = self.add_cluster(bundle=self.required_import_bundle, name="required_import_cluster")

        response = self.client.v2[import_cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertEqual(response.json()["concerns"][0]["owner"]["id"], import_cluster.pk)
        self.assertEqual(response.json()["concerns"][0]["owner"]["type"], "cluster")

    def test_concern_owner_service(self):
        cluster = self.add_cluster(bundle=self.service_requirements_bundle, name="service_requirements_cluster")
        service = self.add_services_to_cluster(service_names=["service_1"], cluster=cluster).get()
        response = self.client.v2[service].get()

        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertEqual(response.json()["concerns"][0]["owner"]["id"], service.pk)
        self.assertEqual(response.json()["concerns"][0]["owner"]["type"], "service")

    def test_adcm_5677_hc_issue_on_link_host_to_cluster_with_plus_constraint(self):
        cluster = self.add_cluster(bundle=self.hc_mapping_constraints_bundle, name="hc_mapping_constraints_cluster")
        service = self.add_services_to_cluster(
            service_names=["service_with_plus_component_constraint"], cluster=cluster
        ).get()
        component = Component.objects.get(prototype__name="plus", service=service, cluster=cluster)

        expected_concern_part = {
            "type": "issue",
            "reason": {
                "message": "${source} has an issue with host-component mapping",
                "placeholder": {
                    "source": {
                        "type": "cluster_mapping",
                        "name": "hc_mapping_constraints_cluster",
                        "params": {"clusterId": cluster.pk},
                    }
                },
            },
            "isBlocking": True,
            "cause": "host-component",
            "owner": {"id": cluster.pk, "type": "cluster"},
        }

        # initial hc concern (from component's constraint)
        response = self.client.v2[cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        actual_concern = response.json()["concerns"][0]
        del actual_concern["id"]
        self.assertDictEqual(actual_concern, expected_concern_part)

        # add host to cluster and map it to `plus` component. Should be no concerns
        provider = self.add_provider(bundle=self.provider_no_config_bundle, name="provider_no_config")
        host_1 = self.add_host(provider=provider, fqdn="host_1", cluster=cluster)
        self.set_hostcomponent(cluster=cluster, entries=((host_1, component),))

        response = self.client.v2[cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 0)

        response = self.client.v2[host_1].get()
        self.assertEqual(len(response.json()["concerns"]), 0)

        # add second host to cluster. Concerns should be on cluster and mapped host (host_1)
        host_2 = self.add_host(provider=provider, fqdn="host_2", cluster=cluster)

        response = self.client.v2[cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        actual_concern = response.json()["concerns"][0]
        del actual_concern["id"]
        self.assertDictEqual(actual_concern, expected_concern_part)

        response = self.client.v2[host_1].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        actual_concern = response.json()["concerns"][0]
        del actual_concern["id"]
        self.assertDictEqual(actual_concern, expected_concern_part)

        # not mapped host has no concerns
        response = self.client.v2[host_2].get()
        self.assertEqual(len(response.json()["concerns"]), 0)

        # unlink host_2 from cluster, 0 concerns on cluster and host_1
        response = self.client.v2[cluster, "hosts", str(host_2.pk)].delete()

        response = self.client.v2[cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 0)

        response = self.client.v2[host_1].get()
        self.assertEqual(len(response.json()["concerns"]), 0)

        # link host_2 to cluster. Concerns should appear again
        response = self.client.v2[cluster, "hosts"].post(data={"hostId": host_2.pk})

        response = self.client.v2[cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        actual_concern = response.json()["concerns"][0]
        del actual_concern["id"]
        self.assertDictEqual(actual_concern, expected_concern_part)

        response = self.client.v2[host_1].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        actual_concern = response.json()["concerns"][0]
        del actual_concern["id"]
        self.assertDictEqual(actual_concern, expected_concern_part)

        # not mapped host has no concerns
        response = self.client.v2[host_2].get()
        self.assertEqual(len(response.json()["concerns"]), 0)

    def test_concerns_on_add_services(self):
        cluster = self.add_cluster(bundle=self.service_add_concerns_bundle, name="service_add_concerns_cluster")
        required_service_concern = {
            "owner_id": cluster.pk,
            "owner_type": ContentType.objects.get_for_model(cluster),
            "cause": "service",
            "name": "service_issue",
        }
        self._check_concerns(object_=cluster, expected_concerns=[required_service_concern])

        service_1 = self.add_services_to_cluster(
            service_names=["service_requires_service_with_many_issues_on_add"], cluster=cluster
        ).get()
        unsatisfied_requirements_concern = {
            "owner_id": service_1.pk,
            "owner_type": ContentType.objects.get_for_model(service_1),
            "cause": "requirement",
            "name": "requirement_issue",
        }
        self._check_concerns(
            object_=cluster, expected_concerns=[required_service_concern, unsatisfied_requirements_concern]
        )
        self._check_concerns(
            object_=service_1, expected_concerns=[required_service_concern, unsatisfied_requirements_concern]
        )

        service_2 = self.add_services_to_cluster(
            service_names=["service_with_many_issues_on_add"], cluster=cluster
        ).get()
        component = service_2.components.get()
        hc_concern = {
            "owner_id": cluster.pk,
            "owner_type": ContentType.objects.get_for_model(cluster),
            "cause": "host-component",
            "name": "host-component_issue",
        }
        config_concern = {
            "owner_id": service_2.pk,
            "owner_type": ContentType.objects.get_for_model(service_2),
            "cause": "config",
            "name": "config_issue",
        }
        import_concern = {
            "owner_id": service_2.pk,
            "owner_type": ContentType.objects.get_for_model(service_2),
            "cause": "import",
            "name": "import_issue",
        }
        self._check_concerns(object_=service_2, expected_concerns=[hc_concern, config_concern, import_concern])
        self._check_concerns(object_=component, expected_concerns=[hc_concern, config_concern, import_concern])
        self._check_concerns(object_=service_1, expected_concerns=[hc_concern])
        self._check_concerns(object_=cluster, expected_concerns=[hc_concern, config_concern, import_concern])


class TestConcernRedistribution(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.bundles_dir = Path(__file__).parent / "bundles"

        self.cluster = self.add_cluster(
            bundle=self.add_bundle(self.bundles_dir / "cluster_all_concerns"), name="With Concerns"
        )

        self.provider = self.add_provider(
            bundle=self.add_bundle(self.bundles_dir / "provider_concerns"), name="Concerned HP"
        )

        self.control_cluster = self.add_cluster(bundle=self.cluster.prototype.bundle, name="Control Cluster")
        self.control_provider = self.add_provider(bundle=self.provider.prototype.bundle, name="Control HP")
        self.control_host = self.add_host(provider=self.control_provider, fqdn="control_host")
        self.control_service = self.add_services_to_cluster(["main"], cluster=self.control_cluster).get()
        self.control_component = self.control_service.components.get(prototype__name="single")

        self.control_concerns = {
            object_: tuple(object_.concerns.all())
            for object_ in (
                self.control_cluster,
                self.control_service,
                self.control_component,
                self.control_provider,
                self.control_host,
            )
        }

        # so flag autogen will work
        self.provider.state = "changed"
        self.provider.save(update_fields=["state"])

    def repr_concerns(self, concerns: Iterable[ConcernItem]) -> str:
        return "\n".join(
            f"  {i}. {rec}"
            for i, rec in enumerate(
                sorted(f"{concern.type} | {concern.cause} from {concern.owner}" for concern in concerns), start=1
            )
        )

    def get_config_issues_of(self, *objects: ADCMEntity) -> tuple[ConcernItem, ...]:
        return ConcernItem.objects.filter(
            self.prepare_objects_filter(*objects), type=ConcernType.ISSUE, cause=ConcernCause.CONFIG
        )

    def get_config_flags_of(self, *objects: ADCMEntity) -> tuple[ConcernItem, ...]:
        return ConcernItem.objects.filter(
            self.prepare_objects_filter(*objects), type=ConcernType.FLAG, cause=ConcernCause.CONFIG
        )

    def prepare_objects_filter(self, *objects: ADCMEntity):
        object_filter = Q()
        for object_ in objects:
            object_filter |= Q(owner_id=object_.id, owner_type=object_.content_type)

        return object_filter

    def check_concerns(self, object_: ADCMEntity, concerns: Iterable[ConcernItem]) -> None:
        expected_concerns = tuple(concerns)
        object_concerns = tuple(object_.concerns.all())

        actual_amount = len(object_concerns)
        expected_amount = len(expected_concerns)

        # avoid calculation of message for success passes
        if actual_amount != expected_amount:
            message = (
                "Incorrect amount of records.\n"
                f"Actual:\n{self.repr_concerns(object_concerns)}\n"
                f"Expected:\n{self.repr_concerns(expected_concerns)}\n"
            )
            self.assertEqual(actual_amount, expected_amount, message)

        for concern in expected_concerns:
            if concern not in object_concerns:
                cur_concern = f"{concern.type} | {concern.cause} from {concern.owner}"
                message = f"\n{cur_concern} not found in:\n{self.repr_concerns(object_concerns)}"
                self.assertIn(concern, object_concerns, message)

    def check_concerns_of_control_objects(self) -> None:
        for object_, expected_concerns in self.control_concerns.items():
            self.check_concerns(object_, expected_concerns)

    def change_mapping_via_api(self, entries: Iterable[tuple[Host, Component]]) -> None:
        response = self.client.v2[self.cluster, "mapping"].post(
            data=[{"hostId": host.id, "componentId": component.id} for host, component in entries]
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def change_mm_via_api(self, mm_value: MM, *objects: Service | Component | Host) -> None:
        for object_ in objects:
            object_endpoint = (
                self.client.v2[object_]
                if not isinstance(object_, Host)
                else self.client.v2[object_.cluster, "hosts", object_]
            )
            self.assertEqual(
                (object_endpoint / "maintenance-mode").post(data={"maintenanceMode": mm_value.value}).status_code,
                HTTP_200_OK,
            )

    def change_config_via_api(self, object_: ADCMEntity) -> None:
        self.assertEqual(
            self.client.v2[object_, "configs"].post(data={"config": {"field": 1}, "adcmMeta": {}}).status_code,
            HTTP_201_CREATED,
        )

    def change_imports_via_api(self, target: Cluster | Service, imports: list[dict]) -> None:
        self.assertEqual(
            self.client.v2[target, "imports"].post(data=imports).status_code,
            HTTP_201_CREATED,
        )

    def test_concerns_swap_on_mapping_changes(self) -> None:
        # prepare
        host_1, host_2, unmapped_host = (
            self.add_host(self.provider, fqdn=f"host_{i}", cluster=self.cluster) for i in range(3)
        )
        unbound_host = self.add_host(self.provider, fqdn="free-host")
        self.change_configuration(host_2, config_diff={"field": 4})
        lower_flag(
            BuiltInFlag.ADCM_OUTDATED_CONFIG.value.name,
            on_objects=[CoreObjectDescriptor(id=host_2.id, type=ADCMCoreType.HOST)],
        )

        main_s = self.add_services_to_cluster(["main"], cluster=self.cluster).get()
        single_c = main_s.components.get(prototype__name="single")
        free_c = main_s.components.get(prototype__name="free")

        require_dummy_s = self.add_services_to_cluster(["require_dummy_service"], cluster=self.cluster).get()
        silent_c = require_dummy_s.components.get(prototype__name="silent")
        sir_c = require_dummy_s.components.get(prototype__name="sir")

        # have to add it to proceed to hc set
        dummy_s = self.add_services_to_cluster(["dummy"], cluster=self.cluster).get()
        dummy_c = dummy_s.components.get()

        # component-less service
        no_components_s = self.add_services_to_cluster(["no_components"], cluster=self.cluster).get()

        # find own concerns
        provider_config_con = self.provider.get_own_issue(ConcernCause.CONFIG)
        host_1_config_con = host_1.get_own_issue(ConcernCause.CONFIG)
        unbound_host_con = unbound_host.get_own_issue(ConcernCause.CONFIG)
        unmapped_host_con = unmapped_host.get_own_issue(ConcernCause.CONFIG)

        main_service_own_con = main_s.get_own_issue(ConcernCause.CONFIG)

        cluster_own_cons = tuple(
            ConcernItem.objects.filter(owner_id=self.cluster.id, owner_type=Cluster.class_content_type)
        )
        main_and_single_cons = (main_service_own_con, single_c.get_own_issue(ConcernCause.CONFIG))
        sir_c_conn = sir_c.get_own_issue(ConcernCause.CONFIG)
        no_components_conn = no_components_s.get_own_issue(ConcernCause.IMPORT)

        with self.subTest("Pre-Mapping Concerns Distribution"):
            self.check_concerns_of_control_objects()

            self.check_concerns(unbound_host, concerns=(provider_config_con, unbound_host_con))
            self.check_concerns(host_1, concerns=(provider_config_con, host_1_config_con))
            self.check_concerns(host_2, concerns=(provider_config_con,))
            self.check_concerns(unmapped_host, concerns=(provider_config_con, unmapped_host_con))

            self.check_concerns(
                self.cluster, concerns=(*cluster_own_cons, *main_and_single_cons, sir_c_conn, no_components_conn)
            )

            self.check_concerns(main_s, concerns=(*cluster_own_cons, *main_and_single_cons))
            self.check_concerns(require_dummy_s, concerns=(*cluster_own_cons, sir_c_conn))
            self.check_concerns(dummy_s, concerns=cluster_own_cons)
            self.check_concerns(no_components_s, concerns=(*cluster_own_cons, no_components_conn))

            self.check_concerns(single_c, concerns=(*cluster_own_cons, *main_and_single_cons))
            self.check_concerns(free_c, concerns=(*cluster_own_cons, main_service_own_con))
            self.check_concerns(silent_c, concerns=cluster_own_cons)
            self.check_concerns(sir_c, concerns=(*cluster_own_cons, sir_c_conn))

        with self.subTest("Fist Mapping Set"):
            hc_concern = self.cluster.get_own_issue(ConcernCause.HOSTCOMPONENT)
            self.assertIsNotNone(hc_concern)

            self.change_mapping_via_api(
                entries=(
                    (host_1, single_c),
                    (host_1, silent_c),
                    (host_2, free_c),
                    (host_2, silent_c),
                    (host_2, sir_c),
                    (host_1, dummy_c),
                ),
            )

            cluster_own_cons = tuple(
                ConcernItem.objects.filter(owner_id=self.cluster.id, owner_type=Cluster.class_content_type)
            )
            self.assertNotIn(hc_concern, cluster_own_cons)

            self.check_concerns(unbound_host, concerns=(provider_config_con, unbound_host_con))
            self.check_concerns(
                host_1, concerns=(provider_config_con, host_1_config_con, *cluster_own_cons, *main_and_single_cons)
            )
            self.check_concerns(
                host_2, concerns=(provider_config_con, *cluster_own_cons, main_service_own_con, sir_c_conn)
            )
            self.check_concerns(unmapped_host, concerns=(provider_config_con, unmapped_host_con))

            self.check_concerns(
                self.cluster,
                concerns=(
                    *cluster_own_cons,
                    *main_and_single_cons,
                    sir_c_conn,
                    no_components_conn,
                    provider_config_con,
                    host_1_config_con,
                ),
            )

            self.check_concerns(
                main_s, concerns=(*cluster_own_cons, *main_and_single_cons, provider_config_con, host_1_config_con)
            )
            self.check_concerns(
                require_dummy_s, concerns=(*cluster_own_cons, sir_c_conn, provider_config_con, host_1_config_con)
            )
            self.check_concerns(no_components_s, concerns=(*cluster_own_cons, no_components_conn))

            self.check_concerns(
                single_c, concerns=(*cluster_own_cons, *main_and_single_cons, provider_config_con, host_1_config_con)
            )
            self.check_concerns(free_c, concerns=(*cluster_own_cons, main_service_own_con, provider_config_con))
            self.check_concerns(silent_c, concerns=(*cluster_own_cons, host_1_config_con, provider_config_con))
            self.check_concerns(sir_c, concerns=(*cluster_own_cons, sir_c_conn, provider_config_con))

            self.check_concerns_of_control_objects()

        with self.subTest("Second Mapping Set"):
            self.change_mapping_via_api(
                entries=((host_2, single_c), (host_2, free_c), (host_1, silent_c), (host_1, dummy_c))
            )

            self.check_concerns(host_1, concerns=(provider_config_con, host_1_config_con, *cluster_own_cons))
            self.check_concerns(host_2, concerns=(provider_config_con, *cluster_own_cons, *main_and_single_cons))
            self.check_concerns(unmapped_host, concerns=(provider_config_con, unmapped_host_con))

            self.check_concerns(
                self.cluster,
                concerns=(
                    *cluster_own_cons,
                    *main_and_single_cons,
                    sir_c_conn,
                    no_components_conn,
                    provider_config_con,
                    host_1_config_con,
                ),
            )

            self.check_concerns(main_s, concerns=(*cluster_own_cons, *main_and_single_cons, provider_config_con))
            self.check_concerns(
                require_dummy_s, concerns=(*cluster_own_cons, sir_c_conn, provider_config_con, host_1_config_con)
            )
            self.check_concerns(no_components_s, concerns=(*cluster_own_cons, no_components_conn))

            self.check_concerns(single_c, concerns=(*cluster_own_cons, *main_and_single_cons, provider_config_con))
            self.check_concerns(free_c, concerns=(*cluster_own_cons, main_service_own_con, provider_config_con))
            self.check_concerns(silent_c, concerns=(*cluster_own_cons, host_1_config_con, provider_config_con))
            self.check_concerns(sir_c, concerns=(*cluster_own_cons, sir_c_conn))

            self.check_concerns_of_control_objects()

    def test_mm_does_not_affect_concerns_distribution(self) -> None:
        # prepare
        second_provider = self.add_provider(bundle=self.provider.prototype.bundle, name="No Concerns HP")
        host_no_concerns = self.add_host(provider=second_provider, fqdn="no-concerns-host", cluster=self.cluster)

        host_1, host_2, unmapped_host = (
            self.add_host(self.provider, fqdn=f"host-{i}", cluster=self.cluster) for i in range(3)
        )

        for object_ in (host_no_concerns, host_2):
            self.change_configuration(object_, config_diff={"field": 1})
            object_desc = CoreObjectDescriptor(id=object_.id, type=orm_object_to_core_type(object_))
            lower_flag(BuiltInFlag.ADCM_OUTDATED_CONFIG.value.name, on_objects=[object_desc])

        main_s, no_components_s = (
            self.add_services_to_cluster(["main", "no_components"], cluster=self.cluster)
            .order_by("prototype__name")
            .all()
        )
        single_c = main_s.components.get(prototype__name="single")
        free_c = main_s.components.get(prototype__name="free")

        # find own concerns
        provider_config_con = self.provider.get_own_issue(ConcernCause.CONFIG)
        second_provider_con = second_provider.get_own_issue(ConcernCause.CONFIG)
        host_1_config_con = host_1.get_own_issue(ConcernCause.CONFIG)
        unmapped_host_con = unmapped_host.get_own_issue(ConcernCause.CONFIG)
        provider_cons = (provider_config_con, second_provider_con)
        all_mapped_hosts_cons = (*provider_cons, host_1_config_con)

        main_service_own_con = main_s.get_own_issue(ConcernCause.CONFIG)
        no_components_service_own_con = no_components_s.get_own_issue(ConcernCause.IMPORT)

        cluster_own_cons = tuple(
            ConcernItem.objects.filter(owner_id=self.cluster.id, owner_type=Cluster.class_content_type)
        )
        single_con = single_c.get_own_issue(ConcernCause.CONFIG)
        main_and_single_cons = (main_service_own_con, single_con)

        def check_concerns():
            self.check_concerns(
                self.cluster, concerns=(*cluster_own_cons, *main_and_single_cons, no_components_service_own_con)
            )
            self.check_concerns(main_s, concerns=(*cluster_own_cons, *main_and_single_cons))
            self.check_concerns(single_c, concerns=(*cluster_own_cons, *main_and_single_cons))
            self.check_concerns(free_c, concerns=(*cluster_own_cons, main_service_own_con))
            self.check_concerns(no_components_s, concerns=(*cluster_own_cons, no_components_service_own_con))

            self.check_concerns(host_1, concerns=(host_1_config_con, provider_config_con))
            self.check_concerns(host_2, concerns=(provider_config_con,))
            self.check_concerns(unmapped_host, concerns=(provider_config_con, unmapped_host_con))
            self.check_concerns(host_no_concerns, concerns=(second_provider_con,))

            self.check_concerns_of_control_objects()

        def check_concerns_after_mapping():
            self.check_concerns(
                self.cluster,
                concerns=(
                    *cluster_own_cons,
                    *main_and_single_cons,
                    no_components_service_own_con,
                    *all_mapped_hosts_cons,
                ),
            )
            self.check_concerns(main_s, concerns=(*cluster_own_cons, *main_and_single_cons, *all_mapped_hosts_cons))
            self.check_concerns(
                single_c,
                concerns=(*cluster_own_cons, *main_and_single_cons, provider_config_con, host_1_config_con),
            )
            self.check_concerns(free_c, concerns=(*cluster_own_cons, main_service_own_con, *all_mapped_hosts_cons))
            self.check_concerns(no_components_s, concerns=(*cluster_own_cons, no_components_service_own_con))

            self.check_concerns(
                host_1, concerns=(*cluster_own_cons, *main_and_single_cons, host_1_config_con, provider_config_con)
            )
            self.check_concerns(
                host_2,
                concerns=(*cluster_own_cons, main_service_own_con, provider_config_con),
            )
            self.check_concerns(unmapped_host, concerns=(provider_config_con, unmapped_host_con))
            self.check_concerns(
                host_no_concerns, concerns=(*cluster_own_cons, main_service_own_con, second_provider_con)
            )

            self.check_concerns_of_control_objects()

        # test
        with self.subTest("Initial state"):
            check_concerns()

        with self.subTest("Unmapped Distribution Turn Service ON"):
            self.change_mm_via_api(MM.ON, main_s)
            check_concerns()

        with self.subTest("Unmapped Distribution Turn Service OFF"):
            self.change_mm_via_api(MM.OFF, main_s)
            check_concerns()

        self.set_hostcomponent(
            cluster=self.cluster,
            entries=((host_1, single_c), (host_1, free_c), (host_2, free_c), (host_no_concerns, free_c)),
        )
        cluster_own_cons = tuple(
            ConcernItem.objects.filter(owner_id=self.cluster.id, owner_type=Cluster.class_content_type)
        )

        with self.subTest("Mapped Turn Component ON"):
            self.change_mm_via_api(MM.ON, single_c)
            check_concerns_after_mapping()

        with self.subTest("Mapped Turn Host ON"):
            self.change_mm_via_api(MM.ON, host_1)
            check_concerns_after_mapping()

        with self.subTest("Mapped Turn Second Host ON"):
            self.change_mm_via_api(MM.ON, host_2)
            check_concerns_after_mapping()

        with self.subTest("Mapped Turn Service Without Components ON"):
            self.change_mm_via_api(MM.ON, no_components_s)
            check_concerns_after_mapping()

        with self.subTest("Mapped Turn All OFF"):
            self.change_mm_via_api(MM.OFF, no_components_s, host_1, host_2, single_c)
            check_concerns_after_mapping()

    def test_concern_removal_with_flag_autogeneration_on_config_change(self) -> None:
        # prepare
        host_1 = self.add_host(self.provider, fqdn="host-1", cluster=self.cluster)
        host_2 = self.add_host(self.provider, fqdn="host-2", cluster=self.cluster)
        unmapped_host = self.add_host(self.provider, fqdn="unmapped-host", cluster=self.cluster)
        another_provider = self.add_provider(bundle=self.provider.prototype.bundle, name="No Concerns HP")
        another_host = self.add_host(provider=another_provider, fqdn="no-concerns-host", cluster=self.cluster)

        main_s = self.add_services_to_cluster(["main"], cluster=self.cluster).get()
        no_components_s = self.add_services_to_cluster(["no_components"], cluster=self.cluster).get()
        single_c = main_s.components.get(prototype__name="single")
        free_c = main_s.components.get(prototype__name="free")

        self.set_hostcomponent(
            cluster=self.cluster,
            entries=((host_1, single_c), (host_1, free_c), (host_2, free_c), (another_host, free_c)),
        )
        self.change_mm_via_api(MM.ON, host_2, single_c)  # ADCM-5882: MM should not affect concerns

        # find own concerns
        no_components_s_own_concern = no_components_s.get_own_issue(ConcernCause.IMPORT)
        main_s_own_concern = main_s.get_own_issue(ConcernCause.CONFIG)
        cluster_own_concerns = tuple(
            ConcernItem.objects.filter(owner_id=self.cluster.id, owner_type=Cluster.class_content_type)
        )
        single_c_concern = single_c.get_own_issue(ConcernCause.CONFIG)
        host_1_concern = host_1.get_own_issue(ConcernCause.CONFIG)
        host_2_concern = host_2.get_own_issue(ConcernCause.CONFIG)
        another_host_concern = another_host.get_own_issue(ConcernCause.CONFIG)
        provider_concern = self.provider.get_own_issue(ConcernCause.CONFIG)
        another_provider_concern = another_provider.get_own_issue(ConcernCause.CONFIG)

        # update states, so flag autogeneration will work as expected
        Host.objects.all().update(state="something")
        Provider.objects.all().update(state="something")
        Cluster.objects.all().update(state="something")
        Service.objects.all().update(state="something")
        Component.objects.all().update(state="something")

        expected_concerns = {}

        def _update_expected_concerns():
            mapped_hosts_concerns = (
                host_1_concern,
                host_2_concern,
                provider_concern,
                another_host_concern,
                another_provider_concern,
            )

            expected_concerns["cluster"] = (
                *cluster_own_concerns,
                main_s_own_concern,
                no_components_s_own_concern,
                single_c_concern,
                *mapped_hosts_concerns,
            )
            expected_concerns["no_components_s"] = (*cluster_own_concerns, no_components_s_own_concern)
            expected_concerns["main_s"] = (
                *cluster_own_concerns,
                main_s_own_concern,
                single_c_concern,
                *mapped_hosts_concerns,
            )
            expected_concerns["free_c"] = [*cluster_own_concerns, main_s_own_concern, *mapped_hosts_concerns]
            expected_concerns["single_c"] = (
                *cluster_own_concerns,
                main_s_own_concern,
                single_c_concern,
                host_1_concern,
                provider_concern,
            )
            expected_concerns["host_1"] = (
                *cluster_own_concerns,
                main_s_own_concern,
                single_c_concern,
                host_1_concern,
                provider_concern,
            )
            expected_concerns["host_2"] = (*cluster_own_concerns, main_s_own_concern, host_2_concern, provider_concern)
            expected_concerns["another_host"] = (
                *cluster_own_concerns,
                main_s_own_concern,
                another_host_concern,
                another_provider_concern,
            )
            expected_concerns["unmapped_host"] = self.get_config_issues_of(unmapped_host, self.provider)
            expected_concerns["provider"] = (provider_concern,)
            expected_concerns["another_provider"] = (another_provider_concern,)

        def check_concerns():
            self.check_concerns(self.cluster, concerns=expected_concerns["cluster"])
            self.check_concerns(no_components_s, concerns=expected_concerns["no_components_s"])
            self.check_concerns(main_s, concerns=expected_concerns["main_s"])
            self.check_concerns(free_c, concerns=expected_concerns["free_c"])
            self.check_concerns(single_c, concerns=expected_concerns["single_c"])

            self.check_concerns(host_1, concerns=expected_concerns["host_1"])
            self.check_concerns(host_2, concerns=expected_concerns["host_2"])
            self.check_concerns(another_host, concerns=expected_concerns["another_host"])
            self.check_concerns(unmapped_host, concerns=expected_concerns["unmapped_host"])
            self.check_concerns(self.provider, concerns=expected_concerns["provider"])
            self.check_concerns(another_provider, concerns=expected_concerns["another_provider"])

            self.check_concerns_of_control_objects()

        # test
        with self.subTest("Initial concerns"):
            _update_expected_concerns()
            check_concerns()

        with self.subTest("Change Provider Config"):
            self.change_config_via_api(another_provider)

            another_provider_concern = self.get_config_flags_of(another_provider)[0]
            _update_expected_concerns()

            check_concerns()

        with self.subTest("Change Host Config"):
            self.change_config_via_api(host_1)

            host_1_concern = self.get_config_flags_of(host_1)[0]
            _update_expected_concerns()

            check_concerns()

        with self.subTest("Change Component in MM Config"):
            self.change_config_via_api(single_c)

            single_c_concern = self.get_config_flags_of(single_c)[0]
            _update_expected_concerns()

            check_concerns()

        with self.subTest("Change Cluster Config"):
            self.change_config_via_api(self.cluster)

            cluster_own_concerns = tuple(
                ConcernItem.objects.filter(owner_id=self.cluster.id, owner_type=Cluster.class_content_type)
            )
            _update_expected_concerns()

            check_concerns()

        with self.subTest("Change Service Config"):
            self.change_config_via_api(main_s)

            main_s_own_concern = self.get_config_flags_of(main_s)[0]
            _update_expected_concerns()

            check_concerns()

    def test_concerns_changes_on_import(self) -> None:
        # prepare
        host_1 = self.add_host(self.provider, fqdn="host-1", cluster=self.cluster)
        host_2 = self.add_host(self.provider, fqdn="host-2", cluster=self.cluster)

        import_s = self.add_services_to_cluster(["with_multiple_imports"], cluster=self.cluster).get()
        component_1, component_2 = import_s.components.order_by("prototype__name")

        self.set_hostcomponent(
            cluster=self.cluster,
            entries=((host_1, component_2),),
        )

        export_cluster = self.add_cluster(self.add_bundle(self.bundles_dir / "cluster_export"), "Exporter")
        export_service = self.add_services_to_cluster(["service_export"], cluster=export_cluster).get()

        # find own concerns
        provider_config_con = self.provider.get_own_issue(ConcernCause.CONFIG)
        host_1_cons = (provider_config_con, host_1.get_own_issue(ConcernCause.CONFIG))
        host_2_cons = (provider_config_con, host_2.get_own_issue(ConcernCause.CONFIG))
        cluster_own_cons = tuple(
            ConcernItem.objects.filter(owner_id=self.cluster.id, owner_type=Cluster.class_content_type)
        )
        component_1_con = component_1.get_own_issue(ConcernCause.CONFIG)

        # test

        self.change_imports_via_api(
            import_s,
            imports=[
                {"source": {"type": "service", "id": export_service.id}},
                {"source": {"type": "cluster", "id": export_cluster.id}},
            ],
        )

        with self.subTest("Set All Imports On Service"):
            self.check_concerns(self.cluster, concerns=(*cluster_own_cons, component_1_con, *host_1_cons))
            self.check_concerns(import_s, concerns=(*cluster_own_cons, component_1_con, *host_1_cons))
            self.check_concerns(component_1, concerns=(*cluster_own_cons, component_1_con))
            self.check_concerns(component_2, concerns=(*cluster_own_cons, *host_1_cons))
            self.check_concerns(host_1, concerns=(*host_1_cons, *cluster_own_cons))
            self.check_concerns(host_2, concerns=host_2_cons)

            self.check_concerns_of_control_objects()

        self.change_imports_via_api(import_s, imports=[{"source": {"type": "service", "id": export_service.id}}])

        # we need to reread it, so it will be correctly searched within the collection
        import_s_con = import_s.get_own_issue(ConcernCause.IMPORT)

        with self.subTest("Set 1/2 Required Imports On Service"):
            self.assertIsNotNone(import_s_con)

            self.check_concerns(self.cluster, concerns=(*cluster_own_cons, import_s_con, component_1_con, *host_1_cons))
            self.check_concerns(import_s, concerns=(*cluster_own_cons, import_s_con, component_1_con, *host_1_cons))
            self.check_concerns(component_1, concerns=(*cluster_own_cons, import_s_con, component_1_con))
            self.check_concerns(component_2, concerns=(*cluster_own_cons, import_s_con, *host_1_cons))
            self.check_concerns(host_1, concerns=(*host_1_cons, import_s_con, *cluster_own_cons))
            self.check_concerns(host_2, concerns=host_2_cons)

            self.check_concerns_of_control_objects()

    def test_concerns_dis_appearance_on_move_cluster_host(self) -> None:
        # prepare
        host_1 = self.add_host(self.provider, fqdn="host-1")
        mapped_host = self.add_host(self.provider, fqdn="mapped-host", cluster=self.cluster)

        greedy_s = self.add_services_to_cluster(["greedy"], cluster=self.cluster).get()
        on_all_c = greedy_s.components.get(prototype__name="on_all")

        # find concerns
        provider_config_con = self.provider.get_own_issue(ConcernCause.CONFIG)
        host_1_cons = (provider_config_con, host_1.get_own_issue(ConcernCause.CONFIG))
        mapped_host_cons = (provider_config_con, mapped_host.get_own_issue(ConcernCause.CONFIG))
        greedy_s_con = greedy_s.get_own_issue(ConcernCause.CONFIG)

        self.set_hostcomponent(cluster=self.cluster, entries=[(mapped_host, on_all_c)])
        self.assertIsNone(self.cluster.get_own_issue(ConcernCause.HOSTCOMPONENT))

        cluster_own_cons = tuple(
            ConcernItem.objects.filter(owner_id=self.cluster.id, owner_type=Cluster.class_content_type)
        )

        # test
        self.assertEqual(
            self.client.v2[self.cluster, "hosts"].post(data={"hostId": host_1.id}).status_code, HTTP_201_CREATED
        )

        with self.subTest("Add Host To Cluster"):
            hc_issue = self.cluster.get_own_issue(ConcernCause.HOSTCOMPONENT)
            self.assertIsNotNone(hc_issue)

            self.check_concerns(self.provider, concerns=(provider_config_con,))
            self.check_concerns(host_1, concerns=host_1_cons)
            self.check_concerns(mapped_host, concerns=(*cluster_own_cons, hc_issue, greedy_s_con, *mapped_host_cons))

            self.check_concerns(self.cluster, concerns=(*cluster_own_cons, hc_issue, greedy_s_con, *mapped_host_cons))
            self.check_concerns(greedy_s, concerns=(*cluster_own_cons, hc_issue, greedy_s_con, *mapped_host_cons))
            self.check_concerns(on_all_c, concerns=(*cluster_own_cons, hc_issue, greedy_s_con, *mapped_host_cons))

            self.check_concerns_of_control_objects()

        self.assertEqual(self.client.v2[self.cluster, "hosts", host_1].delete().status_code, HTTP_204_NO_CONTENT)

        with self.subTest("Remove Host From Cluster"):
            self.assertIsNone(self.cluster.get_own_issue(ConcernCause.HOSTCOMPONENT))

            self.check_concerns(self.provider, concerns=(provider_config_con,))
            self.check_concerns(host_1, concerns=host_1_cons)
            self.check_concerns(mapped_host, concerns=(*cluster_own_cons, greedy_s_con, *mapped_host_cons))

            self.check_concerns(self.cluster, concerns=(*cluster_own_cons, greedy_s_con, *mapped_host_cons))
            self.check_concerns(greedy_s, concerns=(*cluster_own_cons, greedy_s_con, *mapped_host_cons))
            self.check_concerns(on_all_c, concerns=(*cluster_own_cons, greedy_s_con, *mapped_host_cons))

            self.check_concerns_of_control_objects()

    def test_concerns_on_service_deletion(self) -> None:
        # prepare
        greedy_s = self.add_services_to_cluster(["greedy"], cluster=self.cluster).get()

        dummy_s = self.add_services_to_cluster(["dummy"], cluster=self.cluster).get()
        dummy_c = dummy_s.components.get(prototype__name="same_dummy")

        # test
        self.assertIsNotNone(self.cluster.get_own_issue(ConcernCause.HOSTCOMPONENT))

        self.assertEqual(self.client.v2[greedy_s].delete().status_code, HTTP_204_NO_CONTENT)

        hc_issue = self.cluster.get_own_issue(ConcernCause.HOSTCOMPONENT)
        self.assertIsNone(hc_issue)
        cluster_own_cons = tuple(
            ConcernItem.objects.filter(owner_id=self.cluster.id, owner_type=Cluster.class_content_type)
        )

        self.check_concerns(self.cluster, concerns=cluster_own_cons)
        self.check_concerns(dummy_s, concerns=cluster_own_cons)
        self.check_concerns(dummy_c, concerns=cluster_own_cons)

        self.check_concerns_of_control_objects()

    def test_remove_provider(self):
        host_1 = self.add_host_via_api(self.provider, fqdn="host1")
        host_2 = self.add_host_via_api(self.provider, fqdn="host2")
        provider_pk, host_1_pk, host_2_pk = self.provider.pk, host_1.pk, host_2.pk
        another_provider = self.add_provider(
            bundle=Bundle.objects.get(name="provider_with_concerns"), name="Concerned HP 2"
        )

        self.client.v2[host_1].delete()
        self.client.v2[host_2].delete()
        self.client.v2[self.provider].delete()

        self.assertFalse(ConcernItem.objects.filter(owner_id=host_1_pk, owner_type=Host.class_content_type))
        self.assertFalse(ConcernItem.objects.filter(owner_id=host_2_pk, owner_type=Host.class_content_type))
        self.assertFalse(ConcernItem.objects.filter(owner_id=provider_pk, owner_type=Provider.class_content_type))
        self.assertEqual(
            ConcernItem.objects.filter(owner_id=another_provider.pk, owner_type=Provider.class_content_type).count(),
            1,
        )

    def test_remove_host(self):
        host_1 = self.add_host_via_api(self.provider, fqdn="host1")
        host_2 = self.add_host_via_api(self.provider, fqdn="host2")
        host_1_pk = host_1.pk
        another_provider = self.add_provider(
            bundle=Bundle.objects.get(name="provider_with_concerns"), name="Concerned HP 2"
        )
        host_3 = self.add_host_via_api(another_provider, fqdn="host3")

        self.client.v2[host_1].delete()

        self.assertFalse(ConcernItem.objects.filter(owner_id=host_1_pk, owner_type=Host.class_content_type))

        self.assertEqual(host_2.concerns.count(), 2)
        self.assertEqual(host_3.concerns.count(), 2)
        self.assertEqual(self.provider.concerns.count(), 1)
        self.assertEqual(another_provider.concerns.count(), 1)

    def add_host_via_api(self, provider: Provider, fqdn: str) -> Host:
        response = (self.client.v2 / "hosts").post(data={"hostprovider_id": provider.pk, "name": fqdn})
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        return Host.objects.get(fqdn=fqdn)

    def test_host_config_issue(self):
        host = self.add_host_via_api(self.provider, fqdn="host1")

        self.assertIsNotNone(host.get_own_issue(ConcernCause.CONFIG))
        self.assertIsNotNone(self.provider.get_own_issue(ConcernCause.CONFIG))

        #  host config issue resolved, provider remains
        host.state = "changed"
        host.save(update_fields=["state"])
        self.change_config_via_api(host)

        self.assertIsNotNone(self.provider.get_own_issue(ConcernCause.CONFIG))
        self.assertIsNone(host.get_own_issue(ConcernCause.CONFIG))

        host_2 = self.add_host(self.provider, fqdn="host2")
        host_2_config_issue = host_2.get_own_issue(ConcernCause.CONFIG)
        self.assertIsNotNone(host_2_config_issue)
        self.check_concerns(host_2, concerns=(host_2_config_issue, self.provider.get_own_issue(ConcernCause.CONFIG)))

        host_flag = host.concerns.filter(
            type=ConcernType.FLAG,
            owner_id=host.pk,
            owner_type=host.content_type,
            cause=ConcernCause.CONFIG,
        ).first()
        self.check_concerns(host, concerns=(self.provider.get_own_issue(ConcernCause.CONFIG), host_flag))

    def test_two_hosts_config_issue_one_resolved(self):
        host_1 = self.add_host_via_api(self.provider, fqdn="host1")
        host_1.state = "changed"
        host_1.save(update_fields=["state"])
        host_2 = self.add_host_via_api(self.provider, fqdn="host2")

        host_1_config_issue = host_1.get_own_issue(ConcernCause.CONFIG)
        host_2_config_issue = host_2.get_own_issue(ConcernCause.CONFIG)
        provider_config_issue = self.provider.get_own_issue(ConcernCause.CONFIG)

        self.assertIsNotNone(host_1_config_issue)
        self.assertIsNotNone(host_2_config_issue)
        self.assertIsNotNone(provider_config_issue)

        #  host config issue resolved, provider remains
        self.change_config_via_api(host_1)

        self.assertIsNotNone(self.provider.get_own_issue(ConcernCause.CONFIG))
        self.assertIsNone(host_1.get_own_issue(ConcernCause.CONFIG))
        self.assertIsNotNone(host_2.get_own_issue(ConcernCause.CONFIG))

        host_1_flag = host_1.concerns.filter(
            type=ConcernType.FLAG,
            owner_id=host_1.pk,
            owner_type=host_1.content_type,
            cause=ConcernCause.CONFIG,
        ).first()

        self.check_concerns(host_1, concerns=(provider_config_issue, host_1_flag))
        self.check_concerns(host_2, concerns=(provider_config_issue, host_2.get_own_issue(ConcernCause.CONFIG)))

    def test_host_config_issue_from_provider(self):
        host_1 = self.add_host_via_api(self.provider, fqdn="host1")

        host_config_issue = host_1.get_own_issue(ConcernCause.CONFIG)
        provider_config_issue = self.provider.get_own_issue(ConcernCause.CONFIG)

        self.assertIsNotNone(host_config_issue)
        self.assertIsNotNone(provider_config_issue)

        #  provider config issue resolved
        self.change_config_via_api(self.provider)

        host_2 = self.add_host(self.provider, fqdn="host2")

        self.assertIsNone(self.provider.get_own_issue(ConcernCause.CONFIG))
        self.assertIsNotNone(host_1.get_own_issue(ConcernCause.CONFIG))
        self.assertIsNotNone(host_2.get_own_issue(ConcernCause.CONFIG))

        provider_flag = self.provider.concerns.filter(
            type=ConcernType.FLAG,
            owner_id=self.provider.pk,
            owner_type=self.provider.content_type,
            cause=ConcernCause.CONFIG,
        ).first()

        self.check_concerns(
            host_1,
            concerns=(
                provider_flag,
                host_1.get_own_issue(ConcernCause.CONFIG),
            ),
        )
        self.check_concerns(
            host_2,
            concerns=(host_2.get_own_issue(ConcernCause.CONFIG),),
        )

    def test_two_hosts_config_issue_from_provider_resolved(self):
        host_1 = self.add_host_via_api(self.provider, fqdn="host1")
        host_2 = self.add_host_via_api(self.provider, fqdn="host2")

        host_1_config_issue = host_1.get_own_issue(ConcernCause.CONFIG)
        host_2_config_issue = host_2.get_own_issue(ConcernCause.CONFIG)
        provider_config_issue = self.provider.get_own_issue(ConcernCause.CONFIG)

        self.assertIsNotNone(host_1_config_issue)
        self.assertIsNotNone(host_2_config_issue)
        self.assertIsNotNone(provider_config_issue)

        #  provider config issue resolved
        self.change_config_via_api(self.provider)

        self.assertIsNone(self.provider.get_own_issue(ConcernCause.CONFIG))
        self.assertIsNotNone(host_1.get_own_issue(ConcernCause.CONFIG))
        self.assertIsNotNone(host_2.get_own_issue(ConcernCause.CONFIG))

        provider_flag = self.provider.concerns.filter(
            type=ConcernType.FLAG,
            owner_id=self.provider.pk,
            owner_type=self.provider.content_type,
            cause=ConcernCause.CONFIG,
        ).first()

        self.check_concerns(host_1, concerns=(provider_flag, host_1.get_own_issue(ConcernCause.CONFIG)))
        self.check_concerns(host_2, concerns=(provider_flag, host_2.get_own_issue(ConcernCause.CONFIG)))

    def test_dis_appearance_of_require_concern_on_service(self) -> None:
        require_dummy_proto_id = Prototype.objects.get(
            bundle_id=self.cluster.prototype.bundle_id, type="service", name="require_dummy_service"
        ).id

        response = self.client.v2[self.cluster, "services"].post(data={"prototypeId": require_dummy_proto_id})
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        require_dummy_s = Service.objects.get(id=response.json()["id"])
        sir_c = require_dummy_s.components.get(prototype__name="sir")
        silent_c = require_dummy_s.components.get(prototype__name="silent")

        requirement_con = require_dummy_s.get_own_issue(ConcernCause.REQUIREMENT)
        component_config_con = sir_c.get_own_issue(ConcernCause.CONFIG)
        cluster_own_cons = tuple(
            ConcernItem.objects.filter(owner_id=self.cluster.id, owner_type=Cluster.class_content_type)
        )
        expected_concerns = (*cluster_own_cons, requirement_con, component_config_con)

        with self.subTest("Appeared On Add"):
            self.assertIsNotNone(requirement_con)
            self.check_concerns(self.cluster, concerns=expected_concerns)
            self.check_concerns(require_dummy_s, concerns=expected_concerns)
            self.check_concerns(sir_c, concerns=expected_concerns)
            self.check_concerns(silent_c, concerns=(*cluster_own_cons, requirement_con))

        service_proto_id = Prototype.objects.get(
            bundle_id=self.cluster.prototype.bundle_id, type="service", name="required"
        ).id
        self.assertEqual(
            self.client.v2[self.cluster, "services"].post(data={"prototypeId": service_proto_id}).status_code,
            HTTP_201_CREATED,
        )

        # SERVICE concern on cluster is gone, need to reread
        cluster_own_cons = tuple(
            ConcernItem.objects.filter(owner_id=self.cluster.id, owner_type=Cluster.class_content_type)
        )
        expected_concerns = (*cluster_own_cons, requirement_con, component_config_con)

        with self.subTest("Stayed On Unrelated Service Add"):
            self.assertIsNotNone(require_dummy_s.get_own_issue(ConcernCause.REQUIREMENT))
            self.check_concerns(self.cluster, concerns=expected_concerns)
            self.check_concerns(require_dummy_s, concerns=expected_concerns)
            self.check_concerns(sir_c, concerns=expected_concerns)
            self.check_concerns(silent_c, concerns=(*cluster_own_cons, requirement_con))

        dummy_proto_id = Prototype.objects.get(
            bundle_id=self.cluster.prototype.bundle_id, type="service", name="dummy"
        ).id
        response = self.client.v2[self.cluster, "services"].post(data={"prototypeId": dummy_proto_id})
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        dummy_s = Service.objects.get(id=response.json()["id"])

        with self.subTest("Disappeared On Required Service Add"):
            self.assertIsNone(require_dummy_s.get_own_issue(ConcernCause.REQUIREMENT))
            self.check_concerns(self.cluster, concerns=(*cluster_own_cons, component_config_con))
            self.check_concerns(require_dummy_s, concerns=(*cluster_own_cons, component_config_con))
            self.check_concerns(sir_c, concerns=(*cluster_own_cons, component_config_con))
            self.check_concerns(silent_c, concerns=cluster_own_cons)
            self.check_concerns(dummy_s, concerns=cluster_own_cons)
