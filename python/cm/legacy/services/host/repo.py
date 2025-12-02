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


from copy import copy
from dataclasses import dataclass
from pathlib import Path

from core.types import HostID

from cm.legacy.adcm_config.utils import cook_file_type_name
from cm.legacy.services.config.spec import retrieve_flat_spec_for_objects
from cm.models import Host


@dataclass(slots=True)
class DuplicateHostOverrides:
    name: str
    description: str


def get_original_host(host_id: HostID) -> Host:
    return Host.objects.get(original__isnull=True, id=host_id)


def duplicate_host_record(
    host: Host,
    overrides: DuplicateHostOverrides,
) -> Host:
    duplicate = copy(host)

    # erase fields that shouldn't be copied
    duplicate.id = None
    duplicate.config = None
    duplicate.original_id = host.id
    duplicate.cluster = None
    duplicate.maintenance_mode = "off"

    duplicate.fqdn = overrides.name
    duplicate.description = overrides.description

    duplicate.save()

    return duplicate


def prepare_symlinks_for_file_type(duplicate: Host) -> None:
    spec = next(iter(retrieve_flat_spec_for_objects(prototypes=(duplicate.prototype_id,)).values()))

    for composite_key, field in spec.items():
        if field.type not in {"file", "secretfile"}:
            continue

        target_file_path = cook_file_type_name(duplicate.original, *composite_key.split("/"))
        duplicate_file_path = cook_file_type_name(duplicate, *composite_key.split("/"))
        Path(duplicate_file_path).symlink_to(target_file_path)
