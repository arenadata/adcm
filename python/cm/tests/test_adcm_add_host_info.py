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

from unittest import TestCase
from unittest.mock import patch
import sys

from cm.collect_statistics.ansible.action_plugins.adcm_add_host_info import ActionModule


def _build_hostvars(host_id: int, device_data: dict, memtotal_mb: int | str | None) -> dict:
    return {
        "adcm_hostid": host_id,
        "disk_command_out": "",
        "ansible_facts": {
            "_ansible_facts_gathered": True,
            "processor_vcpus": 4,
            "devices": device_data,
            "os_family": "Debian",
            "distribution": "Ubuntu",
            "distribution_version": "22.04",
            "memtotal_mb": memtotal_mb,
        },
    }


def _build_task_vars(host_name: str) -> dict:
    task_vars = {
        "ansible_play_batch": [host_name],
        "hostvars": {
            "host-1-valid": _build_hostvars(
                host_id=1,
                memtotal_mb=2048,
                device_data={
                    "vda": {
                        "sectors": 10,
                        "sectorsize": "512",
                        "removable": "0",
                        "rotational": "1",
                        "size": "12345",
                    }
                },
            ),
            "host-2-empty-values": _build_hostvars(
                host_id=2,
                memtotal_mb="",
                device_data={
                    "vda": {
                        "sectors": "",
                        "sectorsize": "512",
                        "removable": "0",
                        "rotational": "1",
                        "size": "12345",
                    }
                },
            ),
            "host-3-with-none": _build_hostvars(
                host_id=3,
                memtotal_mb=None,
                device_data={
                    "vda": {
                        "sectors": "10",
                        "sectorsize": None,
                        "removable": "0",
                        "rotational": "1",
                        "size": "12345",
                    }
                },
            ),
            "host-4-no-vda": _build_hostvars(host_id=4, device_data={}, memtotal_mb="2048"),
        },
    }
    task_vars["hostvars"] = {host_name: task_vars["hostvars"][host_name]}

    return task_vars


class TestADCMHostInfo(TestCase):
    @classmethod
    def setUpClass(cls):
        # the method "prepare_hosts_facts_for_storage" is static and
        # can test it without a real instance of ActionModule
        cls.prepare_hosts_facts_for_storage = ActionModule.prepare_hosts_facts_for_storage

    def test_prepare_hosts_facts_for_storage(self):
        success_memtotal_mb = 2048
        success_ram_bytes = success_memtotal_mb * 1024**2
        success_disk_size = 5120  # 10 * 512

        cases = [
            ("host-1-valid", 1, success_disk_size, success_ram_bytes),
            ("host-2-empty-values", 2, 0, 0),
            ("host-3-with-none", 3, 0, 0),
            ("host-4-no-vda", 4, 0, success_ram_bytes),
        ]

        for host_name, host_id, expected_disk_size, expected_ram_bytes in cases:
            task_vars = _build_task_vars(host_name=host_name)

            with self.subTest(host_name):
                result = self.prepare_hosts_facts_for_storage(task_vars=task_vars)
                self.assertEqual(result[host_id].facts["disk_size"], expected_disk_size)
                self.assertEqual(result[host_id].facts["ram_bytes"], expected_ram_bytes)

    def test_failed_to_prepare_hosts_facts_for_storage(self):
        task_vars = _build_task_vars(host_name="host-1-valid")
        del task_vars["hostvars"]["host-1-valid"]["ansible_facts"]["memtotal_mb"]

        with patch.object(sys.stderr, "write") as stderr:
            result = self.prepare_hosts_facts_for_storage(task_vars=task_vars)

        self.assertEqual(result, {})
        self.assertIn("Failed to prepare devices record for host-1-valid", stderr.call_args.args[0])
