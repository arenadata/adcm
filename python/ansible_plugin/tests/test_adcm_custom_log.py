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

from unittest.mock import patch

from cm.models import LogStorage
from cm.services.job.run.repo import JobRepoImpl

from ansible_plugin.executors.custom_log import ADCMCustomLogPluginExecutor
from ansible_plugin.tests.base import BaseTestEffectsOfADCMAnsiblePlugins

EXECUTOR_MODULE = "ansible_plugin.executors.custom_log"


class TestEffectsOfADCMAnsiblePlugins(BaseTestEffectsOfADCMAnsiblePlugins):
    EXECUTOR_CLASS = ADCMCustomLogPluginExecutor[lambda _, path: str(path)]

    def test_add_custom_log_by_content_success(self) -> None:
        name = "cool name"
        format_ = "txt"
        content = "bestcontent ever !!!"

        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=self.EXECUTOR_CLASS,
            call_arguments=f"""
                name: {name}
                format: {format_}
                content: "{content}"
            """,
            call_context=job,
        )

        with patch(f"{EXECUTOR_MODULE}.assign_view_logstorage_permissions_by_job") as permissions_mock:
            result = executor.execute()

        self.assertIsNone(result.error)
        self.assertTrue(
            LogStorage.objects.filter(job_id=job.id, type="custom", format=format_, name=name, body=content).exists()
        )
        permissions_mock.assert_called_once()

    def test_path_content(self) -> None:
        name = "cool name"
        format_ = "txt"
        path = "/some/path"

        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=self.EXECUTOR_CLASS,
            call_arguments={"name": name, "format": format_, "path": path},
            call_context=job,
        )

        result = executor.execute()

        self.assertIsNone(result.error)
        log = LogStorage.objects.filter(job_id=job.id, type="custom", format=format_, name=name).get()
        self.assertEqual(log.body, path)

    def test_path_priority_over_content(self) -> None:
        name = "cool name"
        format_ = "txt"
        content = "bestcontent ever !!!"
        path = "/some/path"

        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=self.EXECUTOR_CLASS,
            call_arguments={"name": name, "format": format_, "content": content, "path": path},
            call_context=job,
        )

        with patch(f"{EXECUTOR_MODULE}.assign_view_logstorage_permissions_by_job") as permissions_mock:
            result = executor.execute()

        self.assertIsNone(result.error)
        log = LogStorage.objects.filter(job_id=job.id, type="custom", format=format_, name=name).get()
        self.assertEqual(log.body, path)
        permissions_mock.assert_called_once()
