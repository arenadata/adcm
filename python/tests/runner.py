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

from django.test.runner import DiscoverRunner, ParallelTestSuite, RemoteTestResult, RemoteTestRunner

# Raw patch from https://code.djangoproject.com/ticket/32114
# to prevent pickling problems for `--parallel` + `subTest`
# by retrieving only a part of "required" fields
#
# Note that it may contain less information about the error


class TestCaseForParallelSubTest:
    def __init__(self, test):
        self._m_id = test.id()
        self._m_str = str(test)
        self._m_shortDescription = test.shortDescription()
        if hasattr(test, "test_case"):
            self.test_case = TestCaseForParallelSubTest(test.test_case)
        if hasattr(test, "_subDescription"):
            self._m_subDescription = test._subDescription()

    def _subDescription(self):  # noqa: N802
        return self._m_subDescription

    def id(self):
        return self._m_id

    def shortDescription(self):  # noqa: N802
        return self._m_shortDescription

    def __str__(self):
        return self._m_str


class SubtestSerializingRemoteTestResult(RemoteTestResult):
    def addSubTest(self, test, subtest, err):  # noqa: N802
        subtest = TestCaseForParallelSubTest(subtest)
        super().addSubTest(test, subtest, err)


class SubTestParallelRemoteTestRunner(RemoteTestRunner):
    resultclass = SubtestSerializingRemoteTestResult


class SubTestParallelTestSuite(ParallelTestSuite):
    runner_class = SubTestParallelRemoteTestRunner


class SubTestParallelRunner(DiscoverRunner):
    parallel_test_suite = SubTestParallelTestSuite
