import os
from io import TextIOWrapper

from django.test import TestCase

import task_runner
import job_runner


class TestTaskRunner(TestCase):

    def test_open_file(self):
        root = os.path.dirname(__file__)
        task_id = 'task_id'
        tag = 'tag'
        file_path = "{}/{}-{}.txt".format(root, tag, task_id)
        file_descriptor = task_runner.open_file(root, task_id, tag)
        self.assertTrue(isinstance(file_descriptor, TextIOWrapper))
        self.assertEqual(file_path, file_descriptor.name)
        self.assertTrue(os.path.exists(file_path))
        file_descriptor.close()
        os.remove(file_path)


class TestJobRunner(TestCase):
    pass
