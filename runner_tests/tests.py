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

import os
from io import TextIOWrapper
from unittest.mock import patch, Mock

from django.test import TestCase
from django.utils import timezone
from cm.models import TaskLog, JobLog
import task_runner
import job_runner


class TestTaskRunner(TestCase):

    def setUp(self):
        task = TaskLog(action_id=1, object_id=1, selector={'cluster': 1}, status='success',
                       start_date=timezone.now(), finish_date=timezone.now())
        task.save()
        job = JobLog(task_id=task.id, action_id=task.action_id, selector={'cluster': 1},
                     status='success', start_date=timezone.now(), finish_date=timezone.now())
        job.save()
        super().setUp()

    def test_open_file(self):
        root = os.path.dirname(__file__)
        task_id = 1
        tag = 'tag'
        file_path = "{}/{}-{}.txt".format(root, tag, task_id)
        file_descriptor = task_runner.open_file(root, task_id, tag)
        self.assertTrue(isinstance(file_descriptor, TextIOWrapper))
        self.assertEqual(file_path, file_descriptor.name)
        self.assertTrue(os.path.exists(file_path))
        file_descriptor.close()
        os.remove(file_path)

    def test_get_task(self):
        task = task_runner.get_task(task_id=1)
        self.assertEqual(task.action_id, 1)

    def test_get_jobs(self):
        task = TaskLog.objects.get(id=1)
        jobs = task_runner.get_jobs(task)
        self.assertEqual(jobs[0].action_id, 1)

    @patch('subprocess.Popen')
    def test_run_job(self, mock_subprocess_popen):
        # TODO: added mock for logger
        process_mock = Mock()
        attrs = {'wait.return_value': 0}
        process_mock.configure_mock(**attrs)
        mock_subprocess_popen.return_value = process_mock
        code = task_runner.run_job(1, 1, '', '')
        self.assertEqual(code, 0)

    def test_run_task(self):
        pass

    def test_do(self):
        pass


class TestJobRunner(TestCase):

    def test_open_file(self):
        root = os.path.dirname(__file__)
        job_id = 1
        tag = 'tag'
        file_path = "{}/{}-{}.txt".format(root, tag, job_id)
        file_descriptor = job_runner.open_file(root, job_id, tag)
        self.assertTrue(isinstance(file_descriptor, TextIOWrapper))
        self.assertEqual(file_path, file_descriptor.name)
        self.assertTrue(os.path.exists(file_path))
        file_descriptor.close()
        os.remove(file_path)

    @patch('json.load')
    @patch('builtins.open')
    def test_read_config(self, mock_open, mock_json):
        mock_file_descriptor = Mock()
        mock_file_descriptor.close.return_value = None
        mock_open.return_value = mock_file_descriptor
        mock_json.return_value = {}
        conf = job_runner.read_config(1)
        self.assertDictEqual(conf, {})

    @patch('cm.job.set_job_status')
    def test_set_job_status(self, mock_set_job_status):
        mock_set_job_status.return_value = None
        code = job_runner.set_job_status(1, 0, 1)
        self.assertEqual(code, 0)

    def test_set_pythonpath(self):
        # TODO: is this test needed?
        cmd_env = os.environ.copy()
        python_paths = filter(
            lambda x: x != '',
            ['./pmod'] + cmd_env.get('PYTHONPATH', '').split(':'))
        cmd_env['PYTHONPATH'] = ':'.join(python_paths)
        self.assertDictEqual(cmd_env, job_runner.set_pythonpath())

    def test_run_andible(self):
        pass

    def test_do(self):
        pass
