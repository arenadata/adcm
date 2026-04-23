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

from dataclasses import asdict
import json

from api_v2.log_storage.serializers import LogStorageSerializer
from cm.models import JobLog, LogStorage
from core.logs import CheckLogContent, GroupCheckLogContent, Severity
from django.test import TestCase


class TestLogStorage(TestCase):
    @classmethod
    def setUpTestData(cls):
        job = JobLog.objects.create()
        cls.log_storage = LogStorage.objects.create(job=job, name="check", type="check", format="json", body=None)
        cls.check_log_content = [
            GroupCheckLogContent(
                title="check",
                type="group",
                message="success",
                result=True,
                severity=Severity.ERROR,
                content=[
                    CheckLogContent(
                        title="check", type="check", message="success", result=True, severity=Severity.ERROR
                    )
                ],
            )
        ]
        cls.check_log_content_as_dict = [asdict(item) for item in cls.check_log_content]

    def test_adcm_7994_check_runtime_content_success(self):
        data = LogStorageSerializer(
            instance=self.log_storage,
            context={"retrieve_check_logs_content_for_job": lambda job_id: self.check_log_content},
        ).data
        self.assertListEqual(data["content"], self.check_log_content_as_dict)

    def test_adcm_7994_check_saved_content_success(self):
        self.log_storage.body = json.dumps(self.check_log_content_as_dict)
        self.log_storage.save(update_fields=["body"])
        data = LogStorageSerializer(
            instance=self.log_storage,
            context={"retrieve_check_logs_content_for_job": lambda job_id: []},
        ).data
        self.assertListEqual(data["content"], self.check_log_content_as_dict)
