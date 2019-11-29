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
from unittest.mock import patch, Mock, mock_open

from django.test import TestCase
from django.utils import timezone
from cm.models import TaskLog, JobLog
from cm.logger import log
import task_runner
import job_runner


class PreparationData:

    @staticmethod
    def generate_data(task_number, job_number):
        for tn in range(task_number):
            task_log_data = {
                'action_id': tn + 1,
                'object_id': tn + 1,
                'pid': tn + 1,
                'selector': {'cluster': tn + 1},
                'status': 'success',
                'config': '',
                'hostcomponentmap': '',
                'start_date': timezone.now(),
                'finish_date': timezone.now()
            }
            for jn in range(job_number):
                job_log_data = {
                    'task_id': tn + 1,
                    'action_id': tn + 1,
                    'pid': jn + 1,
                    'selector': {'cluster': tn + 1},
                    'status': 'success',
                    'start_date': timezone.now(),
                    'finish_date': timezone.now()
                }
                yield task_log_data, job_log_data

    @staticmethod
    def preparation_one():
        for task_data, job_data in PreparationData.generate_data(1, 1):
            TaskLog.objects.create(**task_data)
            JobLog.objects.create(**job_data)


class TestTaskRunner(TestCase):

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
        PreparationData.preparation_one()
        task = task_runner.get_task(task_id=1)
        self.assertEqual(task.action_id, 1)

    def test_get_jobs(self):
        PreparationData.preparation_one()
        task = TaskLog.objects.get(id=1)
        jobs = task_runner.get_jobs(task)
        self.assertEqual(jobs[0].action_id, 1)

    @patch.object(log, 'debug')
    @patch('subprocess.Popen')
    def test_run_job(self, mock_subprocess_popen, mock_logger):
        mock_logger.return_value = None
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
    @patch('builtins.open', create=True)
    def test_read_config(self, mo, mock_json):
        mo.side_effect = mock_open(read_data='').return_value
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

    @patch.object(log, 'debug')
    @patch.object(log, 'info')
    @patch('subprocess.Popen')
    @patch('job_runner.open_file')
    @patch('job_runner.read_config')
    def test_run_ansible(self, mock_read_config, mock_open_file, mock_subprocess_popen,
                         mock_log_info, mock_log_debug):

        mock_read_config.return_value = {'job': {'playbook': 'test'}}
        mock_open_file.return_value = None
        mock_open_file.close.return_value = None
        process_mock = Mock()
        attrs = {'wait.return_value': 0}
        process_mock.configure_mock(**attrs)
        mock_subprocess_popen.return_value = process_mock
        mock_log_info.return_value = None
        mock_log_debug.return_value = None
        pass

    def test_do(self):
        pass
