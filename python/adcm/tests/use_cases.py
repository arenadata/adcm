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

from dataclasses import dataclass, field
from pathlib import Path
import tarfile

from cm.models import Bundle
from core.settings import Directories
from faker import Faker
from use_cases.bundle import ParseBundleFromRequest
import dishka


@dataclass(slots=True)
class UseCases:
    container: dishka.Container
    faker: Faker = field(default_factory=Faker)

    def upload_bundle(self, src: Path) -> Bundle:
        with self.container() as container:
            directories = container.get(Directories)

            if src.is_dir():
                archive_path = prepare_bundle_file(source_dir=src, target_dir=directories.downloads)
            else:
                # for "easy" backward compatibility with "upload_and_load_bundle"
                # which accepted path to already packed archive
                archive_path = src

            uc = container.get(ParseBundleFromRequest)
            bundle_id = uc.do(archive=archive_path)

            return Bundle.objects.get(id=bundle_id)


# Utilities


def prepare_bundle_file(source_dir: Path, target_dir: Path) -> Path:
    bundle_file = target_dir / f"{source_dir.name}.tar"

    with tarfile.open(target_dir / bundle_file, "w") as tar:
        for file in source_dir.iterdir():
            tar.add(name=file, arcname=file.name)

    return bundle_file
