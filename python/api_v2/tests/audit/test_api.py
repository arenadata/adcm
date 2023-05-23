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
# pylint: disable=too-many-lines

from datetime import datetime, timedelta

from django.conf import settings
from rest_framework.fields import DateTimeField
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
)

from adcm.tests.base import BaseTestCase


class TestAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.files_dir = settings.BASE_DIR / "python" / "cm" / "tests" / "files"
        self.bundle_adh_name = "adh.1.5.tar"
        self.upload_and_load_bundle(path=self.files_dir / self.bundle_adh_name)

    def test_root_api(self):
        response: Response = self.client.get("/api/v2/")
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_root_audit(self):
        response: Response = self.client.get("/api/v2/audit/")
        response_json = response.json()
        self.assertIn("operations", response_json)
        self.assertIn("logins", response_json)
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_logins(self):
        response: Response = self.client.get("/api/v2/audit/logins/")
        response_json_item = response.data["results"][0]
        current_datetime: datetime = DateTimeField().to_internal_value(response_json_item["login_time"])
        self.assertEqual(response_json_item["login_details"], {"username": "test_user"})

        params_http_200 = {
            "limit": 1,
            "offset": 0,
            "login_result": "success",
            "time_from": current_datetime.date().isoformat(),
            "time_to": (current_datetime + timedelta(hours=1)).date().isoformat(),
        }

        params_http_400 = {
            "login_result": "undefined",
            "time_from": (current_datetime - timedelta(hours=10000)).isoformat(),
            "time_to": (current_datetime - timedelta(hours=10000)).isoformat(),
        }

        for parameter, value in params_http_200.items():
            get_param_response = self.client.get(f"/api/v2/audit/logins/?{parameter}={value}")
            self.assertEqual(get_param_response.status_code, HTTP_200_OK)

        for parameter, value in params_http_400.items():
            get_param_response = self.client.get(f"/api/v2/audit/logins/?{parameter}={value}")
            self.assertEqual(get_param_response.status_code, HTTP_400_BAD_REQUEST)

        self.client.logout()

        for parameter, value in params_http_200.items():
            get_param_response = self.client.get(f"/api/v2/audit/logins/?{parameter}={value}")
            self.assertEqual(get_param_response.status_code, HTTP_401_UNAUTHORIZED)

    def test_operations(self):
        response: Response = self.client.get("/api/v2/audit/operations/")
        response_json_item = response.data["results"][0]
        current_datetime: datetime = DateTimeField().to_internal_value(response_json_item["operation_time"])

        params_http_200 = {
            "limit": 1,
            "offset": 0,
            "time_from": current_datetime.date().isoformat(),
            "time_to": (current_datetime + timedelta(hours=1)).date().isoformat(),
            "username": response_json_item["username"],
            "operation_type": response_json_item["operation_type"],
            "operation_name": response_json_item["operation_name"],
            "object_type": response_json_item["object_type"],
            "object_name": response_json_item["object_name"],
        }

        params_http_400 = {
            "time_from": (current_datetime - timedelta(hours=10000)).isoformat(),
            "time_to": (current_datetime - timedelta(hours=10000)).isoformat(),
            "operation_type": response_json_item["operation_type"] + "_undefined",
            "object_type": response_json_item["object_type"] + "_undefined",
        }

        for parameter, value in params_http_200.items():
            get_param_response = self.client.get(f"/api/v2/audit/operations/?{parameter}={value}")
            self.assertEqual(get_param_response.status_code, HTTP_200_OK)

        for parameter, value in params_http_400.items():
            get_param_response = self.client.get(f"/api/v2/audit/operations/?{parameter}={value}")
            self.assertEqual(get_param_response.status_code, HTTP_400_BAD_REQUEST)

        self.client.logout()

        for parameter, value in params_http_200.items():
            get_param_response = self.client.get(f"/api/v2/audit/operations/?{parameter}={value}")
            self.assertEqual(get_param_response.status_code, HTTP_401_UNAUTHORIZED)
