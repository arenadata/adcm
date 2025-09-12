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

# Liensed under the Apache License, Version 2.0 (the "License");
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
import shutil
import hashlib

from django.conf import settings
from rbac.models import Role

from cm.errors import AdcmEx, raise_adcm_ex
from cm.logger import logger
from cm.models import ADCM, Cluster, JobStatus, ProductCategory, Provider, TaskLog


def delete_bundle(bundle):
    providers = Provider.objects.filter(prototype__bundle=bundle)
    if providers:
        provider = providers[0]
        raise_adcm_ex(
            code="BUNDLE_CONFLICT",
            msg=f'There is provider #{provider.id} "{provider.name}" of bundle '
            f'#{bundle.id} "{bundle.name}" {bundle.version}',
        )

    clusters = Cluster.objects.filter(prototype__bundle=bundle)
    if clusters:
        cluster = clusters[0]
        raise_adcm_ex(
            code="BUNDLE_CONFLICT",
            msg=f'There is cluster #{cluster.id} "{cluster.name}" '
            f'of bundle #{bundle.id} "{bundle.name}" {bundle.version}',
        )

    running_task = (
        TaskLog.objects.select_related("action")
        .filter(status=JobStatus.RUNNING, action__prototype__bundle=bundle)
        .first()
    )
    if running_task is not None:
        raise AdcmEx(
            code="BUNDLE_CONFLICT",
            msg=f'There is running task #{running_task.id} "{running_task.action.display_name}" '
            f'of bundle #{bundle.id} "{bundle.name}" {bundle.version}',
        )

    adcm = ADCM.objects.filter(prototype__bundle=bundle)
    if adcm:
        raise_adcm_ex(
            code="BUNDLE_CONFLICT",
            msg=f'There is adcm object of bundle #{bundle.id} "{bundle.name}" {bundle.version}',
        )
    if bundle.hash != "adcm":
        try:
            shutil.rmtree(Path(settings.BUNDLE_DIR, bundle.hash))
        except FileNotFoundError:
            logger.info(
                "Bundle %s %s was removed in file system. Delete bundle in database",
                bundle.name,
                bundle.version,
            )

    bundle_hash = bundle.hash
    bundle.delete()

    for role in Role.objects.filter(class_name="ParentRole"):
        if not role.child.order_by("id"):
            role.delete()

    ProductCategory.re_collect()

    if bundle_archive := _get_file_hashes(path=settings.DOWNLOAD_DIR).get(bundle_hash):
        bundle_archive.unlink()


def _get_file_hashes(path: Path) -> dict[str, Path]:
    result = {}
    for entry in path.iterdir():
        if not entry.is_file():
            continue
        result[_get_hash(bundle_file=str(entry))] = entry

    return result


def _get_hash(bundle_file: str) -> str:
    sha1 = hashlib.sha1()  # noqa: S324
    with open(bundle_file, "rb") as f:
        for data in iter(lambda: f.read(16384), b""):
            sha1.update(data)

    return sha1.hexdigest()
