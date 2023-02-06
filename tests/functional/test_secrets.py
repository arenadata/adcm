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

"""Test correct appearance of password/secrettext fields in ADCM logs, job logs, inventory"""

import json
from typing import Iterator

import allure
import pytest
from adcm_client.objects import Cluster
from adcm_pytest_plugin.steps.actions import run_cluster_action_and_assert_result
from adcm_pytest_plugin.utils import get_data_dir
from docker.models.containers import Container

# pylint: disable=redefined-outer-name

OLD_PASSWORD = "simplePassword"
NEW_PASSWORD = "veryMuchStrongerstrPassword"
OLD_SECRETTEXT = "This text should be secret\nbut not for your eyes"
NEW_SECRETTEXT = "This is what I am going to tell you\nYou are the best"
OLD_SECRETMAP = {"secret_map_key": "old_secret_map_value"}
NEW_SECRETMAP = {"secret_map_key": "new_secret_map_value"}

# we split secrettext to check if either part of it is in logs, because none should be
SECRETS = [
    OLD_PASSWORD,
    NEW_PASSWORD,
    *OLD_SECRETTEXT.split("\n"),
    *NEW_SECRETTEXT.split("\n"),
    OLD_SECRETMAP["secret_map_key"],
    NEW_SECRETMAP["secret_map_key"],
]

CHANGE_CONFIG_ACTION = "change_secrets"
CHECK_CONFIG_ACTION = "check"

ADCM_LOG_DIR = "/adcm/data/log"
ADCM_RUN_DIR = "/adcm/data/run"


@pytest.fixture()
def configured_cluster(sdk_client_fs) -> Cluster:
    """Upload bundle, create cluster and set password/secrettext"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster"))
    cluster = bundle.cluster_create("Secretly Secret Cluster")
    _set_cluster_secrets(cluster, OLD_PASSWORD, OLD_SECRETTEXT, OLD_SECRETMAP)
    return cluster


def test_secrets_change_via_adcm_config_plugin(adcm_fs, configured_cluster):
    """
    Test that secret config values aren't stored as plaintext in ADCM
    when adcm_config is used
    """
    # run twice to ensure secrets changes doesn't "leak"
    for password, secrettext, secretmap in (
        (NEW_PASSWORD, NEW_SECRETTEXT, NEW_SECRETMAP),
        (OLD_PASSWORD, OLD_SECRETTEXT, OLD_SECRETMAP),
    ):
        job_id = _run_change_config(configured_cluster, password, secrettext, secretmap).job_list()[0].id
        _check_no_secrets_in_config(configured_cluster)
        _check_no_secrets_in_job_dir(adcm_fs.container, job_id)
    _check_no_secrets_in_adcm_logs(adcm_fs.container)


def test_secrets_change_via_config(configured_cluster):
    """
    Test that changing secret fields in adcm doesn't lead to their reveal in object's config
    """
    _check_secrets_in_config_encrypted(configured_cluster)
    _check_no_secrets_in_config(configured_cluster)
    _set_cluster_secrets(configured_cluster, NEW_PASSWORD, NEW_SECRETTEXT, NEW_SECRETMAP)
    _check_secrets_in_config_encrypted(configured_cluster)
    _check_no_secrets_in_config(configured_cluster)


def test_secrets_are_correct_in_job_when_changed_via_plugin(configured_cluster, generic_provider):
    """
    Test that correct secret values are available in job's context
    when they were changed via adcm_config plugin
    """
    configured_cluster.host_add(generic_provider.host_create("some-fqdn"))
    with allure.step("Check secrets set by config change"):
        _run_check_config(configured_cluster, OLD_PASSWORD, OLD_SECRETTEXT, OLD_SECRETMAP)
    with allure.step("Change secrets to new ones with plugin and check"):
        _run_change_config(configured_cluster, NEW_PASSWORD, NEW_SECRETTEXT, NEW_SECRETMAP)
        _run_check_config(configured_cluster, NEW_PASSWORD, NEW_SECRETTEXT, NEW_SECRETMAP)
    with allure.step("Change secrets to old values with plugin and check"):
        _run_change_config(configured_cluster, OLD_PASSWORD, OLD_SECRETTEXT, OLD_SECRETMAP)
        _run_check_config(configured_cluster, OLD_PASSWORD, OLD_SECRETTEXT, OLD_SECRETMAP)


# !===== Checks =====!


def _check_no_secrets_in_config(cluster: Cluster):
    with allure.step(f'Check there are no secrets in "{cluster.name}"'):
        config = cluster.config()
        text_config: str = json.dumps(config, indent=2)
        found_secrets = [secret for secret in SECRETS if secret in text_config]
        if not found_secrets:
            return
        allure.attach(
            text_config,
            name="Config with revealed secrets",
            attachment_type=allure.attachment_type.JSON,
        )
        raise AssertionError("\n".join(("Some of secrets were found in config:", *found_secrets)))


@allure.step("Check that secrets in config are vault-encrypted")
def _check_secrets_in_config_encrypted(cluster: Cluster):
    config = cluster.config()
    secret_config_fields = (
        config["password"],
        config["secrettext"],
        config["secretmap"]["secret_map_key"],
        config["group"]["password"],
        config["group"]["secrettext"],
        config["group"]["secretmap"]["secret_map_key"],
    )
    assert all(
        field.startswith("$ANSIBLE_VAULT") for field in secret_config_fields
    ), f"Not all config fields are encrypted in config:\n{config}"


@allure.step("Check there are no secrets in ADCM log files")
def _check_no_secrets_in_adcm_logs(container: Container):
    exit_code, output = container.exec_run(["ls", "-p", ADCM_LOG_DIR])
    ls_output = output.decode("utf-8")
    if exit_code != 0:
        raise ValueError(f"Failed to get files from {ADCM_LOG_DIR}\nExit code {exit_code}\nOutput: {ls_output}")
    _assert_files_in_dir_for_secrets_absence(container, ADCM_LOG_DIR, ls_output)


@allure.step("Check there are no secrets in files of {job_id}")
def _check_no_secrets_in_job_dir(container: Container, job_id: int):
    # get contents of inventory and config json
    job_dir = f"{ADCM_RUN_DIR}/{job_id}"
    exit_code, output = container.exec_run(["ls", "-p", job_dir])
    ls_output = output.decode("utf-8")
    if exit_code != 0:
        raise ValueError(f"Failed to get files from {job_dir}\nExit code {exit_code}\nOutput: {ls_output}")
    _assert_files_in_dir_for_secrets_absence(container, job_dir, ls_output)


# !===== Utils =====!


def _assert_files_in_dir_for_secrets_absence(container: Container, directory: str, ls_out: str):
    found_secrets = []
    for file in _filtered_files(ls_out):
        filename = f"{directory}/{file}"
        exit_code, output = container.exec_run(["cat", filename])
        file_content = output.decode("utf-8")
        if exit_code != 0:
            raise ValueError(f"Failed to get content of {filename}\nExit code {exit_code}\nOutput: {file_content}")
        for found_secret in (s for s in SECRETS if s in file_content):
            found_message = f'Secret "{found_secret}" found in {filename}'
            found_secrets.append(found_message)
            allure.attach(file_content, name=found_message)
    if found_secrets:
        raise AssertionError("\n".join(("Some of the secrets were found in ADCM log files:\n", *found_secrets)))


def _filtered_files(ls_out: str) -> Iterator[str]:
    """
    Return filter object that returns only files from output of `ls -p` command converted to utf-8 string
    """
    return filter(lambda x: x != "" and x[-1] != "/", ls_out.split("\n"))


def _set_cluster_secrets(cluster: Cluster, password: str, secrettext: str, secretmap: dict):
    secrets = {"password": password, "secrettext": secrettext, "secretmap": secretmap}
    return cluster.config_set({**secrets, "group": {**secrets}})


def _run_change_config(cluster: Cluster, new_password: str, new_secrettext: str, new_secretmap: dict):
    return run_cluster_action_and_assert_result(
        cluster,
        CHANGE_CONFIG_ACTION,
        config={"new_password": new_password, "new_secrettext": new_secrettext, "new_secretmap": new_secretmap},
    )


def _run_check_config(cluster: Cluster, password: str, secrettext: str, secretmap: dict):
    return run_cluster_action_and_assert_result(
        cluster,
        CHECK_CONFIG_ACTION,
        config={"password": password, "secrettext": secrettext, "secretmap": secretmap},
    )
