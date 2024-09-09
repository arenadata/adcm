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

from collections import deque
from datetime import datetime, timezone
from hashlib import md5
from typing import NamedTuple
import re
import sys
import json
import traceback

from ansible.plugins.action import ActionBase

sys.path.append("/adcm/python")

import adcm.init_django  # noqa: F401, isort:skip

from cm.collect_statistics.types import HostDeviceFacts, HostFacts, HostOSFacts
from cm.models import HostInfo
from core.types import HostID

# To parse output of lshw command that'll be like:
#
# H/W path         Device        Class          Description
# =========================================================
# /0/100/1d/0/0    hwmon3        disk           NVMe disk
# /0/100/1d/0/2    /dev/ng0n1    disk           NVMe disk
# /0/100/1d/0/1    /dev/nvme0n1  disk           NVMe disk
#
# It'll try to catch device and description groups
LSHW_PATTERN = re.compile(r"^/[\d\w/]+\s+(?P<device>[\w\d/]+)\s+[^\s]+\s+(?P<description>.+)", flags=re.MULTILINE)


def _extract_disk_info(lshw_out: str) -> dict[str, str]:
    """
    Example

    Input:

    H/W path         Device        Class          Description
    =========================================================
    /0/100/1d/0/0    hwmon3        disk           NVMe disk
    /0/100/1d/0/2    /dev/ng0n1    disk           NVMe disk
    /0/100/1d/0/1    /dev/nvme0n1  disk           NVMe disk

    Output:

    {'hwmon3': 'NVMe disk', 'ng0n1': 'NVMe disk', 'nvme0n1': 'NVMe disk'}
    >>>
    """

    return {
        device.rsplit("/", maxsplit=1)[-1]: description.strip()
        for device, description in LSHW_PATTERN.findall(lshw_out)
    }


class DataToStore(NamedTuple):
    facts: HostFacts
    hash_value: str


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        super().run(tmp=tmp, task_vars=task_vars)

        hosts_facts = self.prepare_hosts_facts_for_storage(task_vars=task_vars)
        self.save_facts(hosts_facts)

        return {"changed": True}

    def prepare_hosts_facts_for_storage(self, task_vars: dict) -> dict[HostID, DataToStore]:
        processed_hosts: dict[HostID, DataToStore] = {}

        hostvars = task_vars["hostvars"]

        for host_name in task_vars["ansible_play_batch"]:
            raw_facts = hostvars[host_name].get("ansible_facts", {})

            # This means that facts weren't gathered for some reason:
            # most likely because it's unreachable
            if not raw_facts or not raw_facts.get("_ansible_facts_gathered", False):
                print(f"Skipping {host_name} due to empty/absent facts")
                continue

            try:
                # if data extraction failed, there won't be such key
                disk_command_out = hostvars[host_name].get("disk_command_out", "")
                disk_descriptions = _extract_disk_info(disk_command_out) if disk_command_out else {}

                host_id = hostvars[host_name]["adcm_hostid"]

                structured_facts = HostFacts(
                    cpu_vcores=raw_facts["processor_vcpus"],
                    os=HostOSFacts(
                        family=raw_facts["os_family"],
                        distribution=raw_facts["distribution"],
                        version=raw_facts["distribution_version"],
                    ),
                    ram=raw_facts["memtotal_mb"],
                    devices=[
                        HostDeviceFacts(
                            name=device_name,
                            removable=device["removable"],
                            rotational=device["rotational"],
                            size=device["size"],
                            description=disk_descriptions.get(device_name, ""),
                        )
                        for device_name, device in raw_facts["devices"].items()
                    ],
                )

                processed_hosts[host_id] = DataToStore(
                    facts=structured_facts,
                    hash_value=md5(json.dumps(structured_facts).encode("utf-8")).hexdigest(),  # noqa: S324
                )
            except Exception as e:  # noqa: BLE001
                message = (
                    f"Failed to prepare devices record for {host_name}: {e}\n" f"Traceback:\n{traceback.format_exc()}\n"
                )
                sys.stderr.write(message)

        return processed_hosts

    def save_facts(self, facts: dict[HostID, DataToStore]) -> None:
        hosts_with_up_to_date_facts = deque()

        for host_id, hash_ in HostInfo.objects.values_list("host_id", "hash").filter(host_id__in=facts.keys()):
            host_info = facts.get(host_id)
            if host_info and host_info.hash_value != hash_:
                continue

            hosts_with_up_to_date_facts.append(host_id)

        # for each batch to have the same datetime
        date = datetime.now(tz=timezone.utc)

        for_update: set[HostID] = set(facts).difference(hosts_with_up_to_date_facts)

        HostInfo.objects.filter(host_id__in=for_update).delete()

        new_hosts_facts = deque()

        for host_id in for_update:
            host_info = facts[host_id]
            new_hosts_facts.append(
                HostInfo(date=date, hash=host_info.hash_value, value=host_info.facts, host_id=host_id)
            )

        HostInfo.objects.bulk_create(new_hosts_facts)
