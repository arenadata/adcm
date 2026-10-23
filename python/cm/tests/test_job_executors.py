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

from cm.legacy.services.job.run.executors import (
    AnsibleExecutorConfig,
    AnsibleProcessExecutor,
    PythonExecutorConfig,
    PythonProcessExecutor,
)
from cm.legacy.utils import get_venv_dir_name

BASE_PATH = "/usr/local/bin:/usr/bin:/bin"


class TestPythonProcessExecutorEnvironment(ParametrizedTestCase):
    """`script_type: python` jobs must run under the venv their bundle declares, not bare `python`."""

    def _build_env(self, venv: str, contract_version: str = "2.1") -> dict:
        executor = PythonProcessExecutor(
            config=PythonExecutorConfig(
                job_script="python_scripts/some_script.py",
                work_dir=Path("/adcm/data/run/1"),
                bundle=BundleInfo(
                    root=Path("/adcm/data/bundle/somehash"), config_dir=Path(), contract_version=contract_version
                ),
                venv=venv,
            )
        )

        with patch.dict("os.environ", {"PATH": BASE_PATH}, clear=True):
            return executor._get_environment_variables()

    @parametrize(
        ("venv", "contract_version", "expected_venv"),
        [
            param("2.16", "2.1", "2.16", id="declared_2_16"),
            param("2.21", "2.1", "2.21-musl", id="declared_2_21"),
            param("2.21", "2.2", "2.21", id="declared_2_21_contract_2_2"),
            param("adcm", "2.1", "adcm", id="declared_adcm"),
        ],
    )
    def test_venv_bin_precedes_base_path(self, venv: str, contract_version: str, expected_venv: str) -> None:
        env = self._build_env(venv=venv, contract_version=contract_version)

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
        self.assertTrue(service_env["PATH"].startswith("/venv/2.21-musl/bin:"))

    def test_bundle_pmod_stays_on_pythonpath(self) -> None:
        # the venv prefix must not displace what ProcessExecutor already sets up
        env = self._build_env(venv="2.16")

        self.assertIn("/adcm/data/bundle/somehash/pmod", env["PYTHONPATH"])


class TestAnsibleProcessExecutorEnvironment(ParametrizedTestCase):
    """Ansible environment is picked by both the declared venv and the bundle's contract version."""

    def _build_env(self, venv: str, contract_version: str) -> dict:
        executor = AnsibleProcessExecutor(
            config=AnsibleExecutorConfig(
                job_script="playbook.yaml",
                work_dir=Path("/adcm/data/run/1"),
                bundle=BundleInfo(
                    root=Path("/adcm/data/bundle/somehash"), config_dir=Path(), contract_version=contract_version
                ),
                tags="",
                verbose=False,
                venv=venv,
                ansible_secret_script=Path("/adcm/python/ansible_secret.py"),
            )
        )

        with patch.dict("os.environ", {"PATH": BASE_PATH}, clear=True):
            return executor._get_environment_variables()

    @parametrize(
        ("venv", "contract_version", "expected_venv"),
        [
            param("2.16", "1.0", "2.16", id="legacy_contract_2_16"),
            param("2.16", "2.0", "2.16", id="contract_2_0_2_16"),
            param("2.16", "2.1", "2.16", id="contract_2_1_2_16"),
            param("2.21", "2.1", "2.21-musl", id="contract_2_1_2_21"),
            param("2.21", "2.2", "2.21", id="contract_2_2_2_21"),
        ],
    )
    def test_venv_dir_depends_on_contract_version(self, venv: str, contract_version: str, expected_venv: str) -> None:
        env = self._build_env(venv=venv, contract_version=contract_version)

        self.assertEqual(env["PATH"], f"/venv/{expected_venv}/bin:{BASE_PATH}")
        self.assertEqual(env["ANSIBLE_COLLECTIONS_PATH"], f"/venv/{expected_venv}/collections")


class TestGetVenvDirName(ParametrizedTestCase):
    @parametrize(
        ("venv", "contract_version", "expected"),
        [
            param("adcm", "2.1", "adcm", id="adcm_venv_is_not_split"),
            param("adcm", "2.2", "adcm", id="adcm_venv_is_not_split_on_2_2"),
            param("2.21", "2.3", "2.21", id="newer_contracts_use_glibc"),
            param("2.21", "3.0", "2.21", id="next_major_uses_glibc"),
        ],
    )
    def test_success(self, venv: str, contract_version: str, expected: str) -> None:
        self.assertEqual(get_venv_dir_name(venv=venv, contract_version=contract_version), expected)
