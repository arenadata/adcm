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
    ClusterObject,
    ConcernCause,
    ConcernItem,
    ConcernType,
    Host,
    HostProvider,
    JobLog,
    ObjectType,
    Prototype,
    PrototypeImport,
    ServiceComponent,
)
from cm.services.concern.flags import BuiltInFlag, lower_flag
from cm.services.concern.messages import ConcernMessage
from cm.tests.mocks.task_runner import RunTaskMock
from core.cluster.types import ObjectMaintenanceModeState as MM  # noqa: N814
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

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

        response: Response = self.client.v2[cluster].get()

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

        response: Response = self.client.v2[cluster].get()

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

        response: Response = self.client.v2[cluster].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertDictEqual(response.json()["concerns"][0]["reason"], expected_concern_reason)

    def test_required_hc_concern(self):
        cluster = self.add_cluster(bundle=self.required_hc_bundle, name="required_hc_cluster")
        self.add_services_to_cluster(service_names=["service_1"], cluster=cluster)
        expected_concern_reason = {
            "message": ConcernMessage.HOST_COMPONENT_ISSUE.template.message,
            "placeholder": {
                "source": {"name": cluster.name, "params": {"clusterId": cluster.pk}, "type": "cluster_mapping"}
            },
        }

        response: Response = self.client.v2[cluster].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertDictEqual(response.json()["concerns"][0]["reason"], expected_concern_reason)

    def test_outdated_config_flag(self):
        cluster = self.add_cluster(bundle=self.config_flag_bundle, name="config_flag_cluster")
        expected_concern_reason = {
            "message": f"{ConcernMessage.FLAG.template.message}outdated config",
            "placeholder": {"source": {"name": cluster.name, "params": {"clusterId": cluster.pk}, "type": "cluster"}},
        }

        response: Response = self.client.v2[cluster, "configs"].post(
            data={"config": {"string": "new_string"}, "adcmMeta": {}, "description": ""},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.v2[cluster].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data["concerns"]), 1)
        concern, *_ = data["concerns"]
        self.assertEqual(concern["type"], "flag")
        self.assertDictEqual(concern["reason"], expected_concern_reason)

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

        response: Response = self.client.v2[service].get()

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

            response: Response = self.client.v2[self.cluster_1].get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(len(response.json()["concerns"]), 1)
            self.assertDictEqual(response.json()["concerns"][0]["reason"], expected_concern_reason)


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

    def _check_concerns(self, object_: Cluster | ClusterObject | ServiceComponent, expected_concerns: list[dict]):
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

        response: Response = self.client.v2[import_cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertEqual(import_cluster.concerns.count(), 1)

        response: Response = self.client.v2[unused_import_cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertEqual(import_cluster.concerns.count(), 1)

        self.client.v2[import_cluster, "imports"].post(
            data=[{"source": {"id": export_cluster.pk, "type": ObjectType.CLUSTER}}],
        )

        response: Response = self.client.v2[import_cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 0)
        self.assertEqual(import_cluster.concerns.count(), 0)

        response: Response = self.client.v2[unused_import_cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertEqual(unused_import_cluster.concerns.count(), 1)

    def test_non_required_import_do_not_raises_concern(self):
        self.assertGreater(PrototypeImport.objects.filter(prototype=self.cluster_2.prototype).count(), 0)

        response: Response = self.client.v2[self.cluster_2].get()
        self.assertEqual(len(response.json()["concerns"]), 0)
        self.assertEqual(self.cluster_2.concerns.count(), 0)

    def test_concern_owner_cluster(self):
        import_cluster = self.add_cluster(bundle=self.required_import_bundle, name="required_import_cluster")

        response: Response = self.client.v2[import_cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertEqual(response.json()["concerns"][0]["owner"]["id"], import_cluster.pk)
        self.assertEqual(response.json()["concerns"][0]["owner"]["type"], "cluster")

    def test_concern_owner_service(self):
        cluster = self.add_cluster(bundle=self.service_requirements_bundle, name="service_requirements_cluster")
        service = self.add_services_to_cluster(service_names=["service_1"], cluster=cluster).get()
        response: Response = self.client.v2[service].get()

        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertEqual(response.json()["concerns"][0]["owner"]["id"], service.pk)
        self.assertEqual(response.json()["concerns"][0]["owner"]["type"], "service")

    def test_adcm_5677_hc_issue_on_link_host_to_cluster_with_plus_constraint(self):
        cluster = self.add_cluster(bundle=self.hc_mapping_constraints_bundle, name="hc_mapping_constraints_cluster")
        service = self.add_services_to_cluster(
            service_names=["service_with_plus_component_constraint"], cluster=cluster
        ).get()
        component = ServiceComponent.objects.get(prototype__name="plus", service=service, cluster=cluster)

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
        response: Response = self.client.v2[cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        actual_concern = response.json()["concerns"][0]
        del actual_concern["id"]
        self.assertDictEqual(actual_concern, expected_concern_part)

        # add host to cluster and map it to `plus` component. Should be no concerns
        provider = self.add_provider(bundle=self.provider_no_config_bundle, name="provider_no_config")
        host_1 = self.add_host(provider=provider, fqdn="host_1", cluster=cluster)
        self.set_hostcomponent(cluster=cluster, entries=((host_1, component),))

        response: Response = self.client.v2[cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 0)

        response: Response = self.client.v2[host_1].get()
        self.assertEqual(len(response.json()["concerns"]), 0)

        # add second host to cluster. Concerns should be on cluster and mapped host (host_1)
        host_2 = self.add_host(provider=provider, fqdn="host_2", cluster=cluster)

        response: Response = self.client.v2[cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        actual_concern = response.json()["concerns"][0]
        del actual_concern["id"]
        self.assertDictEqual(actual_concern, expected_concern_part)

        response: Response = self.client.v2[host_1].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        actual_concern = response.json()["concerns"][0]
        del actual_concern["id"]
        self.assertDictEqual(actual_concern, expected_concern_part)

        # not mapped host has no concerns
        response: Response = self.client.v2[host_2].get()
        self.assertEqual(len(response.json()["concerns"]), 0)

        # unlink host_2 from cluster, 0 concerns on cluster and host_1
        response: Response = self.client.v2[cluster, "hosts", str(host_2.pk)].delete()

        response: Response = self.client.v2[cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 0)

        response: Response = self.client.v2[host_1].get()
        self.assertEqual(len(response.json()["concerns"]), 0)

        # link host_2 to cluster. Concerns should appear again
        response: Response = self.client.v2[cluster, "hosts"].post(data={"hostId": host_2.pk})

        response: Response = self.client.v2[cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        actual_concern = response.json()["concerns"][0]
        del actual_concern["id"]
        self.assertDictEqual(actual_concern, expected_concern_part)

        response: Response = self.client.v2[host_1].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        actual_concern = response.json()["concerns"][0]
        del actual_concern["id"]
        self.assertDictEqual(actual_concern, expected_concern_part)

        # not mapped host has no concerns
        response: Response = self.client.v2[host_2].get()
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
        component = service_2.servicecomponent_set.get()
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
        self.control_component = self.control_service.servicecomponent_set.get(prototype__name="single")

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

    def change_mapping_via_api(self, entries: Iterable[tuple[Host, ServiceComponent]]) -> None:
        response = self.client.v2[self.cluster, "mapping"].post(
            data=[{"hostId": host.id, "componentId": component.id} for host, component in entries]
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def change_mm_via_api(self, mm_value: MM, *objects: ClusterObject | ServiceComponent | Host) -> None:
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

    def change_imports_via_api(self, target: Cluster | ClusterObject, imports: list[dict]) -> None:
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
        single_c = main_s.servicecomponent_set.get(prototype__name="single")
        free_c = main_s.servicecomponent_set.get(prototype__name="free")

        require_dummy_s = self.add_services_to_cluster(["require_dummy_service"], cluster=self.cluster).get()
        silent_c = require_dummy_s.servicecomponent_set.get(prototype__name="silent")
        sir_c = require_dummy_s.servicecomponent_set.get(prototype__name="sir")

        # have to add it to proceed to hc set
        dummy_s = self.add_services_to_cluster(["dummy"], cluster=self.cluster).get()
        dummy_c = dummy_s.servicecomponent_set.get()

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

    def test_concerns_distribution_mm(self) -> None:
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
        single_c = main_s.servicecomponent_set.get(prototype__name="single")
        free_c = main_s.servicecomponent_set.get(prototype__name="free")

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

        # test
        with self.subTest("Unmapped Distribution Turn Service ON"):
            self.change_mm_via_api(MM.ON, main_s)

            self.check_concerns(self.cluster, concerns=(*cluster_own_cons, no_components_service_own_con))
            self.check_concerns(main_s, concerns=(*cluster_own_cons, main_service_own_con))
            self.check_concerns(single_c, concerns=(*cluster_own_cons, single_con))
            self.check_concerns(free_c, concerns=cluster_own_cons)
            self.check_concerns(no_components_s, concerns=(*cluster_own_cons, no_components_service_own_con))

            self.check_concerns(host_1, concerns=(host_1_config_con, provider_config_con))
            self.check_concerns(host_2, concerns=(provider_config_con,))
            self.check_concerns(unmapped_host, concerns=(provider_config_con, unmapped_host_con))
            self.check_concerns(host_no_concerns, concerns=(second_provider_con,))

            self.check_concerns_of_control_objects()

        with self.subTest("Unmapped Distribution Turn Service OFF"):
            self.change_mm_via_api(MM.OFF, main_s)

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

        self.set_hostcomponent(
            cluster=self.cluster,
            entries=((host_1, single_c), (host_1, free_c), (host_2, free_c), (host_no_concerns, free_c)),
        )
        cluster_own_cons = tuple(
            ConcernItem.objects.filter(owner_id=self.cluster.id, owner_type=Cluster.class_content_type)
        )

        with self.subTest("Mapped Turn Component ON"):
            self.change_mm_via_api(MM.ON, single_c)

            self.check_concerns(
                self.cluster,
                concerns=(
                    *cluster_own_cons,
                    main_service_own_con,
                    no_components_service_own_con,
                    *all_mapped_hosts_cons,
                ),
            )
            self.check_concerns(main_s, concerns=(*cluster_own_cons, main_service_own_con, *all_mapped_hosts_cons))
            self.check_concerns(
                single_c,
                concerns=(*cluster_own_cons, *main_and_single_cons, provider_config_con, host_1_config_con),
            )
            self.check_concerns(free_c, concerns=(*cluster_own_cons, main_service_own_con, *all_mapped_hosts_cons))
            self.check_concerns(no_components_s, concerns=(*cluster_own_cons, no_components_service_own_con))

            self.check_concerns(
                host_1, concerns=(*cluster_own_cons, main_service_own_con, host_1_config_con, provider_config_con)
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

        with self.subTest("Mapped Turn Host ON"):
            self.change_mm_via_api(MM.ON, host_1)

            self.check_concerns(
                self.cluster,
                concerns=(*cluster_own_cons, main_service_own_con, no_components_service_own_con, *provider_cons),
            )
            self.check_concerns(main_s, concerns=(*cluster_own_cons, main_service_own_con, *provider_cons))
            self.check_concerns(
                single_c,
                concerns=(*cluster_own_cons, *main_and_single_cons, provider_config_con),
            )
            self.check_concerns(free_c, concerns=(*cluster_own_cons, main_service_own_con, *provider_cons))
            self.check_concerns(no_components_s, concerns=(*cluster_own_cons, no_components_service_own_con))

            self.check_concerns(
                host_1, concerns=(*cluster_own_cons, main_service_own_con, host_1_config_con, provider_config_con)
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

        with self.subTest("Mapped Turn Second Host ON"):
            self.change_mm_via_api(MM.ON, host_2)

            self.check_concerns(
                self.cluster,
                concerns=(*cluster_own_cons, main_service_own_con, no_components_service_own_con, second_provider_con),
            )
            self.check_concerns(main_s, concerns=(*cluster_own_cons, main_service_own_con, second_provider_con))
            self.check_concerns(single_c, concerns=(*cluster_own_cons, *main_and_single_cons))
            self.check_concerns(free_c, concerns=(*cluster_own_cons, main_service_own_con, second_provider_con))
            self.check_concerns(no_components_s, concerns=(*cluster_own_cons, no_components_service_own_con))

            self.check_concerns(
                host_1, concerns=(*cluster_own_cons, main_service_own_con, host_1_config_con, provider_config_con)
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

        with self.subTest("Mapped Turn Service Without Components ON"):
            self.change_mm_via_api(MM.ON, no_components_s)

            self.check_concerns(self.cluster, concerns=(*cluster_own_cons, main_service_own_con, second_provider_con))
            self.check_concerns(main_s, concerns=(*cluster_own_cons, main_service_own_con, second_provider_con))
            self.check_concerns(single_c, concerns=(*cluster_own_cons, *main_and_single_cons))
            self.check_concerns(free_c, concerns=(*cluster_own_cons, main_service_own_con, second_provider_con))
            self.check_concerns(no_components_s, concerns=(*cluster_own_cons, no_components_service_own_con))

            self.check_concerns(
                host_1, concerns=(*cluster_own_cons, main_service_own_con, host_1_config_con, provider_config_con)
            )
            self.check_concerns(
                host_2,
                concerns=(*cluster_own_cons, main_service_own_con, provider_config_con),
            )
            self.check_concerns(unmapped_host, concerns=(provider_config_con, unmapped_host_con))
            self.check_concerns(
                host_no_concerns,
                concerns=(*cluster_own_cons, main_service_own_con, second_provider_con),
            )

            self.check_concerns_of_control_objects()

        with self.subTest("Mapped Turn All OFF"):
            self.change_mm_via_api(MM.OFF, no_components_s, host_1, host_2, single_c)

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
                host_no_concerns,
                concerns=(*cluster_own_cons, main_service_own_con, second_provider_con),
            )

            self.check_concerns_of_control_objects()

    def test_concern_removal_with_flag_autogeneration_on_config_change(self) -> None:
        # prepare
        host_1 = self.add_host(self.provider, fqdn="host-1", cluster=self.cluster)
        host_2 = self.add_host(self.provider, fqdn="host-2", cluster=self.cluster)
        unmapped_host = self.add_host(self.provider, fqdn="unmapped-host", cluster=self.cluster)
        another_provider = self.add_provider(bundle=self.provider.prototype.bundle, name="No Concerns HP")
        another_host = self.add_host(provider=another_provider, fqdn="no-concerns-host", cluster=self.cluster)

        main_s = self.add_services_to_cluster(["main"], cluster=self.cluster).get()
        no_components_s = self.add_services_to_cluster(["no_components"], cluster=self.cluster).get()
        single_c = main_s.servicecomponent_set.get(prototype__name="single")
        free_c = main_s.servicecomponent_set.get(prototype__name="free")

        self.set_hostcomponent(
            cluster=self.cluster,
            entries=((host_1, single_c), (host_1, free_c), (host_2, free_c), (another_host, free_c)),
        )
        self.change_mm_via_api(MM.ON, host_2, single_c)

        # find own concerns
        expected = {}

        no_components_s_own_con = no_components_s.get_own_issue(ConcernCause.IMPORT)
        expected["main_s_own_con"] = main_s.get_own_issue(ConcernCause.CONFIG)
        expected["cluster_own_cons"] = tuple(
            ConcernItem.objects.filter(owner_id=self.cluster.id, owner_type=Cluster.class_content_type)
        )
        expected["single_c_con"] = single_c.get_own_issue(ConcernCause.CONFIG)

        def check_concerns():
            mapped_hosts_concerns = (*expected["host_1_concerns"], *expected["another_host_concerns"])
            self.check_concerns(
                self.cluster,
                concerns=(
                    *expected["cluster_own_cons"],
                    expected["main_s_own_con"],
                    no_components_s_own_con,
                    *mapped_hosts_concerns,
                ),
            )
            self.check_concerns(no_components_s, concerns=(*expected["cluster_own_cons"], no_components_s_own_con))
            self.check_concerns(
                main_s, concerns=(*expected["cluster_own_cons"], expected["main_s_own_con"], *mapped_hosts_concerns)
            )
            self.check_concerns(
                free_c, concerns=(*expected["cluster_own_cons"], expected["main_s_own_con"], *mapped_hosts_concerns)
            )
            self.check_concerns(
                single_c,
                concerns=(
                    *expected["cluster_own_cons"],
                    expected["main_s_own_con"],
                    expected["single_c_con"],
                    *expected["host_1_concerns"],
                ),
            )

            self.check_concerns(
                host_1,
                concerns=(*expected["cluster_own_cons"], expected["main_s_own_con"], *expected["host_1_concerns"]),
            )
            self.check_concerns(
                host_2,
                concerns=(
                    *expected["cluster_own_cons"],
                    expected["main_s_own_con"],
                    *self.get_config_issues_of(host_2, self.provider),
                ),
            )
            self.check_concerns(
                another_host,
                concerns=(
                    *expected["cluster_own_cons"],
                    expected["main_s_own_con"],
                    *expected["another_host_concerns"],
                ),
            )
            self.check_concerns(unmapped_host, concerns=self.get_config_issues_of(unmapped_host, self.provider))
            self.check_concerns(self.provider, concerns=self.get_config_issues_of(self.provider))
            self.check_concerns(another_provider, concerns=self.get_config_flags_of(another_provider))

            self.check_concerns_of_control_objects()

        # test
        self.change_config_via_api(another_provider)

        expected["host_1_concerns"] = self.get_config_issues_of(host_1, self.provider)
        expected["another_host_concerns"] = (
            *self.get_config_issues_of(another_host),
            *self.get_config_flags_of(another_provider),
        )

        with self.subTest("Change HostProvider Config"):
            check_concerns()

        self.change_config_via_api(host_1)

        expected["host_1_concerns"] = (*self.get_config_issues_of(self.provider), *self.get_config_flags_of(host_1))
        expected["another_host_concerns"] = (
            *self.get_config_issues_of(another_host),
            *self.get_config_flags_of(another_provider),
        )

        with self.subTest("Change Host Config"):
            check_concerns()

        self.change_config_via_api(single_c)
        expected["single_c_con"] = self.get_config_flags_of(single_c)[0]

        with self.subTest("Change Component in MM Config"):
            check_concerns()

        self.change_config_via_api(self.cluster)
        expected["cluster_own_cons"] = tuple(
            ConcernItem.objects.filter(owner_id=self.cluster.id, owner_type=Cluster.class_content_type)
        )

        with self.subTest("Change Cluster Config"):
            check_concerns()

        self.change_config_via_api(main_s)
        expected["main_s_own_con"] = self.get_config_flags_of(main_s)[0]

        with self.subTest("Change Service Config"):
            check_concerns()

    def test_concerns_changes_on_import(self) -> None:
        # prepare
        host_1 = self.add_host(self.provider, fqdn="host-1", cluster=self.cluster)
        host_2 = self.add_host(self.provider, fqdn="host-2", cluster=self.cluster)

        import_s = self.add_services_to_cluster(["with_multiple_imports"], cluster=self.cluster).get()
        component_1, component_2 = import_s.servicecomponent_set.order_by("prototype__name")

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
        on_all_c = greedy_s.servicecomponent_set.get(prototype__name="on_all")

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
        dummy_c = dummy_s.servicecomponent_set.get(prototype__name="same_dummy")

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
        self.assertFalse(ConcernItem.objects.filter(owner_id=provider_pk, owner_type=HostProvider.class_content_type))
        self.assertEqual(
            ConcernItem.objects.filter(
                owner_id=another_provider.pk, owner_type=HostProvider.class_content_type
            ).count(),
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

    def add_host_via_api(self, provider: HostProvider, fqdn: str) -> Host:
        response = (self.client.v2 / "hosts").post(data={"hostprovider_id": provider.pk, "name": fqdn})
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        return Host.objects.get(fqdn=fqdn)

    def test_host_config_issue(self):
        host = self.add_host_via_api(self.provider, fqdn="host1")

        self.assertIsNotNone(host.get_own_issue(ConcernCause.CONFIG))
        self.assertIsNotNone(self.provider.get_own_issue(ConcernCause.CONFIG))

        #  host config issue resolved, provider remains
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

    def test_host_config_issue_from_hostprovider(self):
        host_1 = self.add_host_via_api(self.provider, fqdn="host1")

        host_config_issue = host_1.get_own_issue(ConcernCause.CONFIG)
        provider_config_issue = self.provider.get_own_issue(ConcernCause.CONFIG)

        self.assertIsNotNone(host_config_issue)
        self.assertIsNotNone(provider_config_issue)

        #  hostprovider config issue resolved
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

    def test_two_hosts_config_issue_from_hostprovider_resolved(self):
        host_1 = self.add_host_via_api(self.provider, fqdn="host1")
        host_2 = self.add_host_via_api(self.provider, fqdn="host2")

        host_1_config_issue = host_1.get_own_issue(ConcernCause.CONFIG)
        host_2_config_issue = host_2.get_own_issue(ConcernCause.CONFIG)
        provider_config_issue = self.provider.get_own_issue(ConcernCause.CONFIG)

        self.assertIsNotNone(host_1_config_issue)
        self.assertIsNotNone(host_2_config_issue)
        self.assertIsNotNone(provider_config_issue)

        #  hostprovider config issue resolved
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

        require_dummy_s = ClusterObject.objects.get(id=response.json()["id"])
        sir_c = require_dummy_s.servicecomponent_set.get(prototype__name="sir")
        silent_c = require_dummy_s.servicecomponent_set.get(prototype__name="silent")

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

        dummy_s = ClusterObject.objects.get(id=response.json()["id"])

        with self.subTest("Disappeared On Required Service Add"):
            self.assertIsNone(require_dummy_s.get_own_issue(ConcernCause.REQUIREMENT))
            self.check_concerns(self.cluster, concerns=(*cluster_own_cons, component_config_con))
            self.check_concerns(require_dummy_s, concerns=(*cluster_own_cons, component_config_con))
            self.check_concerns(sir_c, concerns=(*cluster_own_cons, component_config_con))
            self.check_concerns(silent_c, concerns=cluster_own_cons)
            self.check_concerns(dummy_s, concerns=cluster_own_cons)
