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

from cm.models import (
    Action,
    JobLog,
    ObjectType,
    Prototype,
    PrototypeImport,
    ServiceComponent,
)
from cm.services.concern.messages import ConcernMessage
from cm.tests.mocks.task_runner import RunTaskMock
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

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

        with self.subTest("Absent on state = 'created'"):
            data = response.json()
            self.assertEqual(len(data["concerns"]), 0)

        cluster.state = "notcreated"
        cluster.save(update_fields=["state"])

        response: Response = self.client.v2[cluster, "configs"].post(
            data={"config": {"string": "new_string"}, "adcmMeta": {}, "description": ""},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.v2[cluster].get()
        self.assertEqual(response.status_code, HTTP_200_OK)

        with self.subTest("Present on another state"):
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

        bundle_dir = self.test_bundles_dir / "provider_no_config"
        self.provider_no_config_bundle = self.add_bundle(source_dir=bundle_dir)

    def test_import_concern_resolved_after_saving_import(self):
        import_cluster = self.add_cluster(bundle=self.required_import_bundle, name="required_import_cluster")
        export_cluster = self.cluster_1

        response: Response = self.client.v2[import_cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertEqual(import_cluster.concerns.count(), 1)

        self.client.v2[import_cluster, "imports"].post(
            data=[{"source": {"id": export_cluster.pk, "type": ObjectType.CLUSTER}}],
        )

        response: Response = self.client.v2[import_cluster].get()
        self.assertEqual(len(response.json()["concerns"]), 0)
        self.assertEqual(import_cluster.concerns.count(), 0)

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
