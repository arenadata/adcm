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

# Since this module is beyond QA responsibility we will not fix docstrings here
# pylint: disable=missing-function-docstring, missing-class-docstring


import os

from django.db import transaction
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework import status

from init_db import init as init_adcm
from rbac.upgrade.role import init_roles


class TestBase(TestCase):
    files_dir = None

    def setUp(self) -> None:
        init_adcm()
        init_roles()

        self.client = Client(HTTP_USER_AGENT="Mozilla/5.0")
        response = self.client.post(
            path=reverse("rbac:token"),
            data={"username": "admin", "password": "admin"},
            content_type="application/json",
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"

        self.client_unauthorized = Client(HTTP_USER_AGENT="Mozilla/5.0")

    def load_bundle(self, bundle_name):
        with open(os.path.join(self.files_dir, bundle_name), encoding="utf-8") as f:
            with transaction.atomic():
                response = self.client.post(
                    path=reverse("upload-bundle"),
                    data={"file": f},
                )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        with transaction.atomic():
            response = self.client.post(
                path=reverse("load-bundle"),
                data={"bundle_file": bundle_name},
            )
            print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
