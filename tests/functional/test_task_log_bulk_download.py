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

"""Tests on downloading all job logs in task as one archive"""

import re
import tarfile
from operator import methodcaller
from os import PathLike
from pathlib import Path
from typing import Callable, Collection, Dict, List, NamedTuple, Set, Union

import allure
import pytest
from adcm_client.objects import ADCM, ADCMClient, Cluster, Component, Host, Provider, Service, Task
from adcm_pytest_plugin.utils import get_data_dir
from docker.models.containers import Container

from tests.functional.ldap_auth.utils import TEST_CONNECTION_ACTION
from tests.functional.tools import AnyADCMObject, ClusterRelatedObject, ProviderRelatedObject
from tests.library.assertions import sets_are_equal

# pylint: disable=redefined-outer-name

CLUSTER_NAME = "Cluster Name"
PROVIDER_NAME = "Provider Name"
CONTENT_DISPOSITION = "Content-Disposition"

filename_regex = re.compile('filename="(.*)"')


class TaskLogInfo(NamedTuple):
    """Helper for storing info about archive naming"""

    action_name: str
    # action's "part" of archive name
    action_in_archive_name: str
    # jobs' parts of directory in archive name
    # {job_id}-{job_archive_name}
    jobs_in_archive: Set[str]


ACTION_NAME_MAP: Dict[str, TaskLogInfo] = {
    tli.action_name: tli
    for tli in (
        TaskLogInfo("without_display_name_simple", "withoutdisplaynamesimple", {"withoutdisplaynamesimple"}),
        TaskLogInfo("without_display_name_s.mpl-x", "withoutdisplaynamesmplx", {"withoutdisplaynamesmplx"}),
        TaskLogInfo("with_display_name_simple", "simple-action-display-name", {"simple-action-display-name"}),
        TaskLogInfo("with_display_name_complex", "very-cool-n4mefor-b3t-actn", {"very-cool-n4mefor-b3t-actn"}),
        TaskLogInfo("complex", "compl3x-task", {"withoutdisplaynamesimple", "wth-diisplaay-n4m3", "ill-just-fail"}),
    )
}
FS_RUN_DIR_FILES = {"inventory.json", "config.json", "ansible-stderr.txt", "ansible-stdout.txt", "ansible.cfg"}
FS_RUN_DIR_FILES_PY = {"inventory.json", "config.json", "python-stderr.txt", "python-stdout.txt", "ansible.cfg"}
DB_RUN_DIR_FILES = {"ansible-stderr.txt", "ansible-stdout.txt"}

# !===== Utilities =====!


def build_full_archive_name(
    adcm_object: Union[Cluster, Service, Component, Provider], task: Task, action_name_in_archive_name: str
) -> str:
    """Build expected archive name for general object action's task"""
    top_level_object = adcm_object if not isinstance(adcm_object, (Service, Component)) else adcm_object.cluster()
    return "_".join(
        map(
            lambda p: p.replace(" ", "-").replace("_", "").lower(),
            (
                top_level_object.name,
                adcm_object.prototype().display_name,
                action_name_in_archive_name,
                str(task.id),
            ),
        )
    )


def build_host_archive_name(host: Host, task: Task, action_name_in_archive_name: str) -> str:
    """Prepare expected name for host action's task"""
    cleaned_fqdn = host.fqdn.replace("-", "").replace(".", "")
    return f"{cleaned_fqdn}_{action_name_in_archive_name}_{task.id}"


def get_filenames_from_archive(archive: Path) -> List[str]:
    """Extract names from an archive"""
    with tarfile.open(archive) as tar:
        return tar.getnames()


def get_unique_directory_names(names_in_archive: Collection[str]) -> Set[str]:
    """Get unique names of directories extracted from archive names"""
    return {n.split("/", maxsplit=1)[0] for n in names_in_archive}


def get_unique_directory_names_wo_job_id(names_in_archive: Collection[str]) -> Set[str]:
    """Get unique names of directories extracted from archive names (task id is removed)"""
    return {n.split("-", maxsplit=1)[1] for n in get_unique_directory_names(names_in_archive)}


def get_files_from_dir(dirname: str, names_in_archive: Collection[str]) -> Set[str]:
    """Extract filenames that belong to a given directory"""
    return {dir_and_file[-1] for n in names_in_archive if dirname in (dir_and_file := n.rsplit("/", maxsplit=1))[0]}


def _get_task_of(adcm_object: Union[ClusterRelatedObject, ProviderRelatedObject], client: ADCMClient) -> Task:
    object_type = adcm_object.__class__.__name__.lower()
    object_task = next(
        filter(
            lambda task: task.object_type == object_type and task.object_id == adcm_object.id,
            map(methodcaller("task"), client.job_list()),
        ),
        None,
    )
    if object_task is None:
        raise RuntimeError(f"Suitable task not found for {adcm_object}")
    return object_task


# !===== Steps and Checks =====!


def run_all_actions(adcm_object: AnyADCMObject) -> List[Task]:
    """Run all actions on object"""
    tasks = []
    for action in adcm_object.action_list():
        tasks.append(action.run())
        tasks[-1].wait()
    return tasks


def check_archive_name(archive: Path, expected_name: str) -> None:
    """Check archive file name"""
    with allure.step(f"Check archive name is {expected_name}"):
        assert (
            actual := archive.with_suffix("").stem
        ) == expected_name, f"Incorrect archive name.\nExpected: {expected_name}\nActual: {actual}"


def check_job_directories(
    filenames: List[str],
    jobs_in_archive: Set[str],
    dir_name_extractor: Callable[[List[str]], Set[str]] = get_unique_directory_names_wo_job_id,
) -> None:
    """Check that archive contains directories of all jobs"""
    with allure.step("Check that archive contains directories of all jobs"):
        sets_are_equal(
            dir_name_extractor(filenames),
            jobs_in_archive,
            "Incorrect job directory names in archive",
        )


def check_all_files_presented_in_all_directories(
    filenames: List[str], jobs_in_archive: Set[str], expected_files: Set[str]
) -> None:
    """
    Check that in each directory of an archive (job's directories) there are all required files (logs, configs, etc.)
    """
    for dirname in jobs_in_archive:
        with allure.step(f"Check content of directory {dirname} in an archive"):
            sets_are_equal(
                get_files_from_dir(dirname, filenames),
                expected_files,
                f"Incorrect files in '{dirname}' job's directory in archive",
            )


def check_archive_naming(adcm_object, task: Task, expected_files: Set[str], name_builder: Callable, tmpdir: PathLike):
    """Check archive name, names of jobs' directories in it and filenames in all directories"""
    with allure.step(f"Check task logs archive download from {adcm_object.__class__}'s action"):
        archive: Path = task.download_logs(tmpdir)
        archive_task_info = ACTION_NAME_MAP[task.action().name]
        check_archive_name(archive, name_builder(adcm_object, task, archive_task_info.action_in_archive_name))
        filenames = get_filenames_from_archive(archive)
        check_job_directories(filenames, archive_task_info.jobs_in_archive)
        check_all_files_presented_in_all_directories(filenames, archive_task_info.jobs_in_archive, expected_files)


@allure.step("Remove downloaded archives")
def remove_archives(tmpdir: PathLike) -> None:
    """Remove downloaded archives"""
    directory = Path(tmpdir)
    for archive in filter(lambda file: set(file.suffixes) == {"tar", "gz"}, directory.iterdir()):
        archive.unlink()


# !===== Fixtures ======!


@pytest.fixture(params=["naming"])
def cluster(request, sdk_client_fs) -> Cluster:
    """Create cluster"""
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, request.param, "cluster")).cluster_create(CLUSTER_NAME)


@pytest.fixture(params=["naming"])
def provider(request, sdk_client_fs) -> Provider:
    """Create provider"""
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, request.param, "provider")).provider_create(
        PROVIDER_NAME
    )


@pytest.fixture()
def _prepare_cluster_and_provider(cluster, provider) -> None:
    cluster.service_add(name="service_proto_name")
    provider.host_create("just-fqdn.domain")


# !===== Tests ======!


@pytest.mark.usefixtures("_prepare_cluster_and_provider")
def test_naming(cluster, provider, adcm_fs, sdk_client_fs, tmpdir):
    """Test naming of task's archive and its contents"""
    _test_archiving_adcm_task(sdk_client_fs.adcm(), tmpdir)
    service = cluster.service()
    for adcm_object in (cluster, service, service.component(), provider):
        _test_archiving_general_object_task(adcm_object, tmpdir)
    _test_archiving_host_task(provider.host(), tmpdir)
    remove_archives(tmpdir)
    _test_archiving_from_db(sdk_client_fs, adcm_fs.container, tmpdir)
    remove_archives(tmpdir)
    _test_no_prototype(sdk_client_fs, tmpdir)


@allure.step("Test ADCM's task archive naming")
def _test_archiving_adcm_task(adcm: ADCM, tmpdir: PathLike) -> None:
    clean_action_name = "test-ldap-connection"
    adcm.config_set_diff(
        {
            "attr": {"ldap_integration": {"active": True}},
            "config": {
                "ldap_integration": {k: k for k in ("ldap_uri", "ldap_user", "ldap_password", "user_search_base")}
            },
        }
    )
    task = adcm.action(name=TEST_CONNECTION_ACTION).run()
    task.wait()
    with allure.step("Download task logs and check naming"):
        archive = task.download_logs(tmpdir)
        check_archive_name(archive, f"adcm_{clean_action_name}_{task.id}")
        filenames = get_filenames_from_archive(archive)
        check_job_directories(filenames, {clean_action_name})
        check_all_files_presented_in_all_directories(filenames, {clean_action_name}, expected_files=FS_RUN_DIR_FILES_PY)


def _test_archiving_general_object_task(
    adcm_object: Union[Cluster, Service, Component, Provider], tmpdir: PathLike
) -> None:
    with allure.step(f"Test {adcm_object.__class__.__name__}'s task archive naming"):
        for task in run_all_actions(adcm_object):
            check_archive_naming(adcm_object, task, FS_RUN_DIR_FILES, build_full_archive_name, tmpdir)


@allure.step("Test Host's task archive naming")
def _test_archiving_host_task(host: Host, tmpdir: PathLike) -> None:
    for task in run_all_actions(host):
        check_archive_naming(host, task, FS_RUN_DIR_FILES, build_host_archive_name, tmpdir)


def _test_archiving_from_db(client: ADCMClient, adcm_container: Container, tmpdir: PathLike) -> None:
    with allure.step("Remove all task log directories from FS"):
        exit_code, output = adcm_container.exec_run(["sh", "-c", "rm -r /adcm/data/run/*"])
        if exit_code != 0:
            raise RuntimeError(f"Failed to remove task log directories from FS: {output.decode('utf-8')}")
    for adcm_object in (client.cluster(), client.service(), client.component(), client.provider()):
        check_archive_naming(
            adcm_object, _get_task_of(adcm_object, client), DB_RUN_DIR_FILES, build_full_archive_name, tmpdir
        )
    host = client.host()
    check_archive_naming(host, _get_task_of(host, client), DB_RUN_DIR_FILES, build_host_archive_name, tmpdir)


@allure.step("Test tasks without action's prototype")
def _test_no_prototype(client: ADCMClient, tmpdir: PathLike) -> None:
    objects = client.cluster(), client.service(), client.component(), client.provider(), client.host()
    each_object_tasks: List[Task] = [_get_task_of(adcm_object, client) for adcm_object in objects]
    with allure.step("Delete all bundles"):
        client.host().delete()
        client.provider().delete()
        client.cluster().delete()
        for bundle in client.bundle_list():
            bundle.delete()
    with allure.step("Check logs download of task with no action prototype"):
        for task in each_object_tasks:
            job_ids = {str(job.id) for job in task.job_list()}
            archive: Path = task.download_logs(tmpdir)
            check_archive_name(archive, str(task.id))
            filenames = get_filenames_from_archive(archive)
            check_job_directories(filenames, job_ids, get_unique_directory_names)
            check_all_files_presented_in_all_directories(filenames, job_ids, DB_RUN_DIR_FILES)
