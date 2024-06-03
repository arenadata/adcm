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

from cm.models import ADCM, CheckLog, GroupCheckLog, LogStorage, ServiceComponent
from cm.services.job.run.repo import JobRepoImpl

from ansible_plugin.errors import PluginValidationError
from ansible_plugin.executors.check import ADCMCheckPluginExecutor
from ansible_plugin.tests.base import BaseTestEffectsOfADCMAnsiblePlugins

EXECUTOR_MODULE = "ansible_plugin.executors.check"


class TestCheckPluginExecutor(BaseTestEffectsOfADCMAnsiblePlugins):
    def setUp(self) -> None:
        super().setUp()

        self.adcm = ADCM.objects.first()
        self.service_1 = self.add_services_to_cluster(["service_1"], cluster=self.cluster).first()
        self.component_1 = ServiceComponent.objects.filter(service=self.service_1).first()

        self.add_host_to_cluster(self.cluster, self.host_1)

    def test_adcm_check_success(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMCheckPluginExecutor,
            call_arguments="""
                title: title
                result: true
                msg: test_message
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsNone(result.error)
        self.assertIsNone(None)
        self.assertTrue(result.changed)

    def test_adcm_check_no_title_fail(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMCheckPluginExecutor,
            call_arguments="""
                result: true
                msg: test_message
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsInstance(result.error, PluginValidationError)
        self.assertIn("Arguments doesn't match expected schema", result.error.message)
        self.assertDictEqual(result.value, {})
        self.assertFalse(result.changed)

    def test_adcm_check_no_result_fail(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMCheckPluginExecutor,
            call_arguments="""
                title: title
                msg: test_message
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsInstance(result.error, PluginValidationError)
        self.assertIn("Arguments doesn't match expected schema", result.error.message)
        self.assertDictEqual(result.value, {})
        self.assertFalse(result.changed)

    def test_adcm_check_no_msg_fail(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMCheckPluginExecutor,
            call_arguments="""
                title: title
                result: False
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsInstance(result.error, PluginValidationError)
        self.assertIn("Arguments doesn't match expected schema", result.error.message)
        self.assertDictEqual(result.value, {})
        self.assertFalse(result.changed)

    def test_adcm_check_no_msg_but_there_success_msg_fail(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMCheckPluginExecutor,
            call_arguments="""
                title: title
                result: True
                success_msg: success
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsInstance(result.error, PluginValidationError)
        self.assertIn("Arguments doesn't match expected schema", result.error.message)
        self.assertDictEqual(result.value, {})
        self.assertFalse(result.changed)

    def test_adcm_check_no_msg_but_there_fail_msg_fail(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMCheckPluginExecutor,
            call_arguments="""
                title: title
                result: False
                fail_msg: fail
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsInstance(result.error, PluginValidationError)
        self.assertIn("Arguments doesn't match expected schema", result.error.message)
        self.assertDictEqual(result.value, {})
        self.assertFalse(result.changed)

    def test_adcm_check_no_msg_but_there_success_msg_and_fail_msg_success(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMCheckPluginExecutor,
            call_arguments="""
                title: title
                result: False
                success_msg: success
                fail_msg: fail
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsNone(result.error)
        self.assertIsNone(None)
        self.assertTrue(result.changed)

    def test_adcm_check_no_msg_and_there_success_msg_and_fail_msg_success(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMCheckPluginExecutor,
            call_arguments="""
                title: title
                result: False
                success_msg: success
                fail_msg: fail
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsNone(result.error)
        self.assertEqual(result.value, "")
        self.assertTrue(result.changed)

    def test_adcm_check_group_title_and_group_success_msg_success(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMCheckPluginExecutor,
            call_arguments="""
                title: title
                result: true
                msg: test_message
                group_title: group
                group_success_msg: success group
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsNone(result.error)
        self.assertIsNone(None)
        self.assertTrue(result.changed)

    def test_adcm_check_group_title_and_group_fail_msg_success(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMCheckPluginExecutor,
            call_arguments="""
                title: title
                result: true
                msg: test_message
                group_title: group
                group_fail_msg: fail group
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsNone(result.error)
        self.assertIsNone(None)
        self.assertTrue(result.changed)

    def test_adcm_check_group_title_no_group_msg_but_there_msg_success(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMCheckPluginExecutor,
            call_arguments="""
                title: title
                result: true
                msg: test_message
                group_title: group
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsNone(result.error)
        self.assertEqual(result.value, "")
        self.assertTrue(result.changed)

    def test_adcm_check_group_title_no_group_msg_fail(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMCheckPluginExecutor,
            call_arguments="""
                title: title
                result: true
                group_title: group
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsInstance(result.error, PluginValidationError)
        self.assertIn("Arguments doesn't match expected schema", result.error.message)
        self.assertDictEqual(result.value, {})
        self.assertFalse(result.changed)

    def test_adcm_check_double_call_val_success(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMCheckPluginExecutor,
            call_arguments="""
                title: title
                result: true
                msg: test_message
                group_title: group
                group_success_msg: success group
            """,
            call_context=job,
        )
        executor.execute()
        result = executor.execute()

        self.assertEqual(result.value, "")
        self.assertTrue(result.changed)

        self.assertEqual(GroupCheckLog.objects.all().count(), 1)
        self.assertEqual(CheckLog.objects.all().count(), 2)
        self.assertEqual(LogStorage.objects.all().count(), 3)

    def test_adcm_check_double_call_fail(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMCheckPluginExecutor,
            call_arguments="""
                title: title
                result: true
                group_title: group
            """,
            call_context=job,
        )
        executor.execute()
        result = executor.execute()

        self.assertIsInstance(result.error, PluginValidationError)
        self.assertIn("Arguments doesn't match expected schema", result.error.message)
        self.assertDictEqual(result.value, {})
        self.assertFalse(result.changed)

        self.assertEqual(GroupCheckLog.objects.all().count(), 0)
        self.assertEqual(CheckLog.objects.all().count(), 0)
        self.assertEqual(LogStorage.objects.all().count(), 2)
