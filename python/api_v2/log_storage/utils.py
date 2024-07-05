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

from datetime import datetime, timezone
from pathlib import Path
import io
import tarfile

from adcm import settings
from cm.models import (
    ActionType,
    ClusterObject,
    Host,
    JobLog,
    LogStorage,
    ServiceComponent,
    TaskLog,
)
from cm.utils import str_remove_non_alnum


def get_task_download_archive_name(task: TaskLog) -> str:
    archive_name = f"{task.pk}.tar.gz"

    if not task.action:
        return archive_name

    archive_name = f"{str_remove_non_alnum(value=task.action.display_name or task.action.name)}_{archive_name}"

    if not task.task_object:
        return archive_name

    if not isinstance(task.task_object, Host):
        action_name = str_remove_non_alnum(value=task.action.prototype.display_name or task.action.prototype.name)
        archive_name = f"{action_name}_{archive_name}"

    if isinstance(task.task_object, (ClusterObject, ServiceComponent)):
        object_name = task.task_object.cluster.display_name
    else:
        object_name = task.task_object.display_name

    return f"{str_remove_non_alnum(value=object_name)}_{archive_name}"


def get_task_download_archive_file_handler(task: TaskLog) -> io.BytesIO:
    jobs = JobLog.objects.filter(task=task)

    if task.action and task.action.type == ActionType.JOB:
        task_dir_name_suffix = str_remove_non_alnum(value=task.action.display_name) or str_remove_non_alnum(
            value=task.action.name,
        )
    else:
        task_dir_name_suffix = None

    file_handler = io.BytesIO()
    with tarfile.open(fileobj=file_handler, mode="w:gz") as tar_file:
        for job in jobs:
            if task_dir_name_suffix is None:
                dir_name_suffix = str_remove_non_alnum(value=job.display_name or "") or str_remove_non_alnum(
                    value=job.name
                )
            else:
                dir_name_suffix = task_dir_name_suffix

            directory = Path(settings.RUN_DIR, str(job.pk))
            if directory.is_dir():
                files = [item for item in Path(settings.RUN_DIR, str(job.pk)).iterdir() if item.is_file()]
                for log_file in files:
                    tarinfo = tarfile.TarInfo(f'{f"{job.pk}-{dir_name_suffix}".strip("-")}/{log_file.name}')
                    tarinfo.size = log_file.stat().st_size
                    tarinfo.mtime = log_file.stat().st_mtime
                    tar_file.addfile(tarinfo=tarinfo, fileobj=io.BytesIO(log_file.read_bytes()))
            else:
                log_storages = LogStorage.objects.filter(job=job, type__in={"stdout", "stderr"})
                for log_storage in log_storages:
                    tarinfo = tarfile.TarInfo(
                        f'{f"{job.pk}-{dir_name_suffix}".strip("-")}' f"/{log_storage.name}-{log_storage.type}.txt",
                    )
                    # using `or ""` here to avoid passing None to `bytes`
                    body = io.BytesIO(bytes(log_storage.body or "", settings.ENCODING_UTF_8))
                    tarinfo.size = body.getbuffer().nbytes
                    tarinfo.mtime = datetime.now(tz=timezone.utc).timestamp()
                    tar_file.addfile(tarinfo=tarinfo, fileobj=body)

    return file_handler
