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

from operator import itemgetter

from cm.models import Bundle, ObjectType, ProductCategory, Prototype
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.tests.base import BaseAPITestCase


class TestPrototype(BaseAPITestCase):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        cluster_bundle_1_path = self.test_bundles_dir / "cluster_one"
        cluster_bundle_2_path = self.test_bundles_dir / "cluster_one_upgrade"

        self.bundle_1 = self.add_bundle(source_dir=cluster_bundle_1_path)
        self.bundle_2 = self.add_bundle(source_dir=cluster_bundle_2_path)

        self.cluster_1_prototype: Prototype = self.bundle_1.prototype_set.filter(type=ObjectType.CLUSTER).first()

        self.prototype_ids = list(Prototype.objects.exclude(name="ADCM").values_list("pk", flat=True))

    def test_list_success(self):
        response = (self.client.v2 / "prototypes").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], len(self.prototype_ids))

    def test_versions_cluster_success(self):
        response = (self.client.v2 / "prototypes" / "versions").get(query={"type": ObjectType.CLUSTER.value})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(len(response.json()[0]["versions"]), 2)

    def test_retrieve_success(self):
        response = self.client.v2[self.cluster_1_prototype].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.cluster_1_prototype.pk)

    def test_retrieve_not_found_fail(self):
        response = (self.client.v2 / "prototypes" / str(self.get_non_existent_pk(model=Prototype))).get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_accept_license_success(self):
        response = self.client.v2[self.cluster_1_prototype, "license", "accept"].post(data=None)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.cluster_1_prototype.refresh_from_db(fields=["license"])
        self.assertEqual(self.cluster_1_prototype.license, "accepted")

    def test_accept_non_existing_license_fail(self):
        prototype_without_license = Prototype.objects.exclude(name="ADCM").filter(license="absent").first()
        response = self.client.v2[prototype_without_license, "license", "accept"].post(data=None)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_filter_by_bundle_id_and_type_cluster(self):
        response = (self.client.v2 / "prototypes").get(query={"bundleId": self.bundle_1.id, "type": "cluster"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_filtering_success(self):
        prototype = Prototype.objects.filter(name="cluster_one").first()
        prototype.description = "Custom description"
        prototype.version = "1.2.3"
        prototype.license = "accepted"
        prototype.save()

        filters = {
            "id": (prototype.pk, None, 0),
            "name": (prototype.name, prototype.name[1:-3].upper(), "wrong"),
            "description": (prototype.description, prototype.description[4:-3].upper(), "wrong"),
            "displayName": (prototype.display_name, prototype.display_name[1:-3].upper(), "wrong"),
            "version": (prototype.version, prototype.version[1:].upper(), "wrong"),
            "type": (ObjectType.CLUSTER.value, None, ObjectType.ADCM.value),
            "license": ("absent", None, "accepted"),
        }

        def get_expected_items_number(_filter_name: str) -> tuple[int, int | None, int]:
            match _filter_name:
                case "description" | "id" | "adcmMinVersion" | "path":
                    return 1, 1, 0
                case "displayName" | "name":
                    return 2, 2, 0
                case "version":
                    return 1, 1, 0
                case "type":
                    return 2, 1, 0
                case "license":
                    return 21, 0, 1

        for filter_name, (correct_value, partial_value, wrong_value) in filters.items():
            found_exact_items, found_items_partially, found_items_wrongly = get_expected_items_number(filter_name)
            with self.subTest(filter_name=filter_name):
                response = (self.client.v2 / "prototypes").get(query={filter_name: correct_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], found_exact_items)

                response = (self.client.v2 / "prototypes").get(query={filter_name: wrong_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], found_items_wrongly)

                if partial_value:
                    response = (self.client.v2 / "prototypes").get(query={filter_name: partial_value})
                    self.assertEqual(response.status_code, HTTP_200_OK)
                    self.assertEqual(response.json()["count"], found_items_partially)

    def test_ordering_success(self):
        prototype = Prototype.objects.filter(name="cluster_one").first()
        prototype.description = "Custom description"
        prototype.version = "1.2.3"
        prototype.license = "accepted"
        prototype.save()

        ordering_fields = {
            "id": "id",
            "name": "name",
            "display_name": "displayName",
            "description": "description",
            "version": "version",
            "type": "type",
            "license": "license",
        }

        def get_ordering_results(response):
            if ordering_field != "license":
                return [provider[ordering_field] for provider in response.json()["results"]]
            elif ordering_field == "license":
                return [provider[ordering_field]["status"] for provider in response.json()["results"]]

        for model_field, ordering_field in ordering_fields.items():
            with self.subTest(ordering_field=ordering_field):
                response = (self.client.v2 / "prototypes").get(query={"ordering": ordering_field})
                self.assertEqual(response.status_code, HTTP_200_OK)

                self.assertListEqual(
                    get_ordering_results(response),
                    list(
                        Prototype.objects.exclude(type="adcm").order_by(model_field).values_list(model_field, flat=True)
                    ),
                )

                response = (self.client.v2 / "prototypes").get(query={"ordering": f"-{ordering_field}"})
                self.assertEqual(response.status_code, HTTP_200_OK)

                self.assertListEqual(
                    get_ordering_results(response),
                    list(
                        Prototype.objects.exclude(type="adcm")
                        .order_by(f"-{model_field}")
                        .values_list(model_field, flat=True)
                    ),
                )


class TestPrototypeVersion(BaseAPITestCase):
    def setUp(self):
        super().setUp()

        for version in ("1", "2"):
            name = "ServFirst"
            bundle = Bundle.objects.create(
                name=name, version=version, hash="q", category=ProductCategory.objects.get_or_create(value=name)[0]
            )
            for proto_type, display_name in [
                ("service", name),
                ("service", "another"),
                ("cluster", name),
                ("component", name),
                ("component", "another"),
            ]:
                Prototype.objects.create(
                    bundle=bundle, type=proto_type, name=display_name, display_name=display_name, version=version
                )

            name = "ClustFirst"
            bundle = Bundle.objects.create(
                name=name, version=version, hash="c", category=ProductCategory.objects.get_or_create(value=name)[0]
            )
            for proto_type, display_name in [
                ("cluster", name),
                ("service", name),
                ("service", "another"),
                ("component", name),
                ("component", "another"),
            ]:
                Prototype.objects.create(
                    bundle=bundle, type=proto_type, name=display_name, display_name=display_name, version=version
                )

            name = "CompFirst"
            bundle = Bundle.objects.create(
                name=name, version=version, hash="co", category=ProductCategory.objects.get_or_create(value=name)[0]
            )
            for proto_type, display_name in [
                ("component", name),
                ("component", "another"),
                ("cluster", name),
                ("service", name),
                ("service", "another"),
            ]:
                Prototype.objects.create(
                    bundle=bundle, type=proto_type, name=display_name, display_name=display_name, version=version
                )

            name = "HostFirst"
            bundle = Bundle.objects.create(
                name=name, version=version, hash="h", category=ProductCategory.objects.get_or_create(value=name)[0]
            )
            for proto_type, display_name in [("host", name), ("provider", name)]:
                Prototype.objects.create(
                    bundle=bundle, type=proto_type, name=display_name, display_name=display_name, version=version
                )

            name = "HostProviderFirst"
            bundle = Bundle.objects.create(
                name=name, version=version, hash="hp", category=ProductCategory.objects.get_or_create(value=name)[0]
            )
            for proto_type, display_name in [
                ("provider", name),
                ("host", name),
            ]:
                Prototype.objects.create(
                    bundle=bundle, type=proto_type, name=display_name, display_name=display_name, version=version
                )

    def test_absent_cluster_candidate_bug_4851(self):
        response = (self.client.v2 / "prototypes" / "versions").get(query={"type": ObjectType.CLUSTER.value})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            sorted(map(itemgetter("name"), response.json())),
            sorted(["ServFirst", "ClustFirst", "CompFirst", self.bundle_1.name, self.bundle_2.name]),
        )

    def test_absent_hostprovider_candidate_bug_4851(self):
        response = (self.client.v2 / "prototypes" / "versions").get(query={"type": ObjectType.PROVIDER.value})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            sorted(map(itemgetter("name"), response.json())),
            sorted(["HostProviderFirst", "HostFirst", self.provider_bundle.name]),
        )

    def test_child_filters_disallowed_failed(self):
        for disallowed_type in (ObjectType.ADCM, ObjectType.SERVICE, ObjectType.COMPONENT, ObjectType.HOST):
            with self.subTest(msg=disallowed_type.value):
                response = (self.client.v2 / "prototypes" / "versions").get(query={"type": disallowed_type.value})

                self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
                self.assertIn(f"{disallowed_type.value} is not one of the available choices", response.json()["desc"])

    def test_no_filter_success(self):
        # provider mocking cluster name
        name = "ClustFirst"
        bundle = Bundle.objects.create(
            name=name, version="3", hash="c", category=ProductCategory.objects.get_or_create(value=name)[0]
        )
        Prototype.objects.create(bundle=bundle, type="provider", name=name, display_name=name, version="3")

        response = (self.client.v2 / "prototypes" / "versions").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            sorted(map(itemgetter("name"), response.json())),
            sorted(
                [
                    "ServFirst",
                    "ClustFirst",
                    "ClustFirst",
                    "CompFirst",
                    self.bundle_1.name,
                    self.bundle_2.name,
                    "HostProviderFirst",
                    "HostFirst",
                    self.provider_bundle.name,
                ]
            ),
        )
