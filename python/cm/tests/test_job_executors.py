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

from pathlib import Path
from unittest.mock import patch

from core.action import BundleInfo
from unittest_parametrize import ParametrizedTestCase, param, parametrize

from cm.legacy.services.job.run.executors import PythonExecutorConfig, PythonProcessExecutor

BASE_PATH = "/usr/local/bin:/usr/bin:/bin"


class TestPythonProcessExecutorEnvironment(ParametrizedTestCase):
    """`script_type: python` jobs must run under the venv their bundle declares, not bare `python`."""

    def _build_env(self, venv: str) -> dict:
        executor = PythonProcessExecutor(
            config=PythonExecutorConfig(
                job_script="python_scripts/some_script.py",
                work_dir=Path("/adcm/data/run/1"),
                bundle=BundleInfo(root=Path("/adcm/data/bundle/somehash"), config_dir=Path()),
                venv=venv,
            )
        )

        with patch.dict("os.environ", {"PATH": BASE_PATH}, clear=True):
            return executor._get_environment_variables()

    @parametrize(
        ("venv", "expected_venv"),
        [
            param("2.16", "2.16", id="declared_2_16"),
            param("2.21", "2.21", id="declared_2_21"),
        ],
    )
    def test_venv_bin_precedes_base_path(self, venv: str, expected_venv: str) -> None:
        env = self._build_env(venv=venv)

        # first entry wins when the OS resolves `python`, so prepending is the whole point
        self.assertEqual(env["PATH"], f"/venv/{expected_venv}/bin:{BASE_PATH}")

    def test_bare_interpreter_is_not_reachable_first(self) -> None:
        # regression: the executor used to inherit PATH untouched, so `python` was the base
        # image interpreter, which has neither django nor python-ldap
        env = self._build_env(venv="2.16")

        self.assertNotEqual(env["PATH"], BASE_PATH)
        self.assertTrue(env["PATH"].startswith("/venv/2.16/bin:"))

    def test_same_bundle_may_use_different_venvs(self) -> None:
        # a service can override the cluster's venv, so the venv is resolved per job, not per bundle
        cluster_env = self._build_env(venv="2.16")
        service_env = self._build_env(venv="2.21")

        self.assertTrue(cluster_env["PATH"].startswith("/venv/2.16/bin:"))
        self.assertTrue(service_env["PATH"].startswith("/venv/2.21/bin:"))

    def test_bundle_pmod_stays_on_pythonpath(self) -> None:
        # the venv prefix must not displace what ProcessExecutor already sets up
        env = self._build_env(venv="2.16")

        self.assertIn("/adcm/data/bundle/somehash/pmod", env["PYTHONPATH"])
