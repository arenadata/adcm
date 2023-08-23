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

from api_v2.tests.base import BaseAPITestCase
from cm.models import KnownNames, MessageTemplate, ObjectType, Prototype
from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED


class TestConcernsResponse(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle_dir = settings.BASE_DIR / "python" / "api_v2" / "tests" / "bundles" / "cluster_with_required_service"
        self.required_service_bundle = self.add_bundle(source_dir=bundle_dir)

        bundle_dir = (
            settings.BASE_DIR / "python" / "api_v2" / "tests" / "bundles" / "cluster_with_required_config_field"
        )
        self.required_config_bundle = self.add_bundle(source_dir=bundle_dir)

        bundle_dir = settings.BASE_DIR / "python" / "api_v2" / "tests" / "bundles" / "cluster_with_required_import"
        self.required_import_bundle = self.add_bundle(source_dir=bundle_dir)

        bundle_dir = settings.BASE_DIR / "python" / "api_v2" / "tests" / "bundles" / "cluster_with_required_hc"
        self.required_hc_bundle = self.add_bundle(source_dir=bundle_dir)

        bundle_dir = settings.BASE_DIR / "python" / "api_v2" / "tests" / "bundles" / "cluster_with_allowed_flags"
        self.config_flag_bundle = self.add_bundle(source_dir=bundle_dir)

        bundle_dir = settings.BASE_DIR / "python" / "api_v2" / "tests" / "bundles" / "cluster_with_service_requirements"
        self.service_requirements_bundle = self.add_bundle(source_dir=bundle_dir)

    def test_required_service_concern(self):
        cluster = self.add_cluster(bundle=self.required_service_bundle, name="required_service_cluster")
        expected_concern_reason = {
            "message": MessageTemplate.objects.get(name=KnownNames.REQUIRED_SERVICE_ISSUE.value).template["message"],
            "placeholder": {
                "source": {"type": "cluster", "name": cluster.name, "params": {"clusterId": cluster.pk}},
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

        response: Response = self.client.get(path=reverse(viewname="v2:cluster-detail", kwargs={"pk": cluster.pk}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertDictEqual(response.json()["concerns"][0]["reason"], expected_concern_reason)

    def test_required_config_concern(self):
        cluster = self.add_cluster(bundle=self.required_config_bundle, name="required_config_cluster")
        expected_concern_reason = {
            "message": MessageTemplate.objects.get(name=KnownNames.CONFIG_ISSUE.value).template["message"],
            "placeholder": {"source": {"name": cluster.name, "params": {"clusterId": cluster.pk}, "type": "cluster"}},
        }

        response: Response = self.client.get(path=reverse(viewname="v2:cluster-detail", kwargs={"pk": cluster.pk}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertDictEqual(response.json()["concerns"][0]["reason"], expected_concern_reason)

    def test_required_import_concern(self):
        cluster = self.add_cluster(bundle=self.required_import_bundle, name="required_import_cluster")
        expected_concern_reason = {
            "message": MessageTemplate.objects.get(name=KnownNames.REQUIRED_IMPORT_ISSUE.value).template["message"],
            "placeholder": {"source": {"name": cluster.name, "params": {"clusterId": cluster.pk}, "type": "cluster"}},
        }

        response: Response = self.client.get(path=reverse(viewname="v2:cluster-detail", kwargs={"pk": cluster.pk}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertDictEqual(response.json()["concerns"][0]["reason"], expected_concern_reason)

    def test_required_hc_concern(self):
        cluster = self.add_cluster(bundle=self.required_hc_bundle, name="required_hc_cluster")
        self.add_service_to_cluster(service_name="service_1", cluster=cluster)
        expected_concern_reason = {
            "message": MessageTemplate.objects.get(name=KnownNames.HOST_COMPONENT_ISSUE.value).template["message"],
            "placeholder": {"source": {"name": cluster.name, "params": {"clusterId": cluster.pk}, "type": "cluster"}},
        }

        response: Response = self.client.get(path=reverse(viewname="v2:cluster-detail", kwargs={"pk": cluster.pk}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertDictEqual(response.json()["concerns"][0]["reason"], expected_concern_reason)

    def test_outdated_config_flag(self):
        cluster = self.add_cluster(bundle=self.config_flag_bundle, name="config_flag_cluster")
        expected_concern_reason = {
            "message": MessageTemplate.objects.get(name=KnownNames.CONFIG_FLAG.value).template["message"],
            "placeholder": {"source": {"name": cluster.name, "params": {"clusterId": cluster.pk}, "type": "cluster"}},
        }

        response: Response = self.client.post(
            path=reverse(viewname="v2:cluster-config-list", kwargs={"cluster_pk": cluster.pk}),
            data={"config": {"string": "new_string"}, "attr": {}, "description": ""},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.get(path=reverse(viewname="v2:cluster-detail", kwargs={"pk": cluster.pk}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertDictEqual(response.json()["concerns"][0]["reason"], expected_concern_reason)

    def test_service_requirements(self):
        cluster = self.add_cluster(bundle=self.service_requirements_bundle, name="service_requirements_cluster")
        service = self.add_service_to_cluster(service_name="service_1", cluster=cluster)
        expected_concern_reason = {
            "message": MessageTemplate.objects.get(name=KnownNames.UNSATISFIED_REQUIREMENT_ISSUE.value).template[
                "message"
            ],
            "placeholder": {
                "source": {
                    "name": service.name,
                    "params": {"clusterId": cluster.pk, "serviceId": service.pk},
                    "type": "service",
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

        response: Response = self.client.get(
            path=reverse(viewname="v2:service-detail", kwargs={"cluster_pk": cluster.pk, "pk": service.pk})
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["concerns"]), 1)
        self.assertDictEqual(response.json()["concerns"][0]["reason"], expected_concern_reason)
