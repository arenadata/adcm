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

from cm.models import Action, Provider
from cm.tests.mocks.task_runner import RunTaskMock
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.tests.base import BaseAPITestCase


class TestProvider(BaseAPITestCase):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        host_provider_path = self.test_bundles_dir / "provider"

        self.host_provider_bundle = self.add_bundle(source_dir=host_provider_path)
        self.host_provider = self.add_provider(self.host_provider_bundle, "test host provider")

    def test_list_success(self):
        response = (self.client.v2 / "hostproviders").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_retrieve_success(self):
        response = self.client.v2[self.host_provider].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.host_provider.pk)

    def test_retrieve_not_found_fail(self):
        response = (self.client.v2 / "hostproviders" / str(self.get_non_existent_pk(model=Provider))).get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_create_success(self):
        response = (self.client.v2 / "hostproviders").post(
            data={
                "prototypeId": self.host_provider_bundle.pk,
                "name": self.host_provider.name + " new",
                "description": "newly created host provider",
            },
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(response.json()["name"], self.host_provider.name + " new")

    def test_create_no_description_success(self):
        response = (self.client.v2 / "hostproviders").post(
            data={
                "prototypeId": self.host_provider_bundle.pk,
                "name": self.host_provider.name + " new",
            },
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(response.json()["name"], self.host_provider.name + " new")

    def test_host_provider_duplicate_fail(self):
        response = (self.client.v2 / "hostproviders").post(
            data={
                "prototype": self.host_provider.pk,
                "name": self.host_provider.name,
                "description": self.host_provider.description,
            },
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_delete_success(self):
        response = self.client.v2[self.host_provider].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertFalse(Provider.objects.filter(pk=self.host_provider.pk).exists())

    def test_delete_not_found_fail(self):
        response = (self.client.v2 / "hostproviders" / str(self.get_non_existent_pk(model=Provider))).delete()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_filtering_success(self):
        self.add_provider(self.host_provider_bundle, "second test host provider")
        self.host_provider.state = "installed"
        self.host_provider.description = "newly created host provider"
        self.host_provider.save()
        filters = {
            "name": (self.host_provider.name, self.host_provider.name[7:-3].upper(), "wrong"),
            "state": (self.host_provider.state, None, "wrong"),
            "prototypeDisplayName": (self.host_provider.prototype.display_name, None, "wrong"),
        }

        for filter_name, (correct_value, partial_value, wrong_value) in filters.items():
            with self.subTest(filter_name=filter_name):
                exact_items = 2 if filter_name in ("name", "prototypeDisplayName") else 1

                response = (self.client.v2 / "hostproviders").get(query={filter_name: correct_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], exact_items)

                response = (self.client.v2 / "hostproviders").get(query={filter_name: wrong_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

                if partial_value:
                    response = (self.client.v2 / "hostproviders").get(query={filter_name: partial_value})
                    self.assertEqual(response.status_code, HTTP_200_OK)
                    self.assertEqual(response.json()["count"], 2)

    def test_ordering_success(self):
        self.add_provider(self.host_provider_bundle, "second test host provider")
        self.add_provider(self.host_provider_bundle, "third test host provider")

        response = (self.client.v2 / "hostproviders").get(query={"ordering": "name"})

        self.assertListEqual(
            [provider["name"] for provider in response.json()["results"]],
            ["second test host provider", "test host provider", "third test host provider"],
        )

        response = (self.client.v2 / "hostproviders").get(query={"ordering": "-name"})
        self.assertListEqual(
            [provider["name"] for provider in response.json()["results"]],
            ["third test host provider", "test host provider", "second test host provider"],
        )


class TestProviderActions(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.action = Action.objects.get(prototype=self.provider.prototype, name="provider_action")

    def test_action_list_success(self):
        response = self.client.v2[self.provider, "actions"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_action_retrieve_success(self):
        response = self.client.v2[self.provider, "actions", self.action].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

    def test_action_run_success(self):
        with RunTaskMock() as run_task:
            response = self.client.v2[self.provider, "actions", self.action, "run"].post(
                data={"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False},
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], run_task.target_task.id)
        self.assertEqual(run_task.target_task.status, "created")

        run_task.runner.run(run_task.target_task.id)
        run_task.target_task.refresh_from_db()
        self.assertEqual(run_task.target_task.status, "success")
