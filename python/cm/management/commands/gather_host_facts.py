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

import os
import sys
import json
import subprocess

from django.conf import settings
from django.core.management import BaseCommand

from cm.collect_statistics.gather_hardware_info import get_inventory
from cm.utils import get_env_with_venv_path


class Command(BaseCommand):
    help = "Gather hardware facts about hosts"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._inventory_dir = settings.DATA_DIR / "tmp" / "gather_host_facts"
        self._workdir = settings.CODE_DIR / "cm" / "collect_statistics" / "ansible"

    def handle(self, *_, **__) -> None:
        self._inventory_dir.mkdir(exist_ok=True, parents=True)

        inventory_file = self._inventory_dir / "inventory.json"

        with inventory_file.open(mode="w", encoding="utf-8") as file_:
            json.dump(get_inventory(), file_)

        os.chdir(self._workdir)

        ansible_command = [
            "ansible-playbook",
            "--vault-password-file",
            str(settings.CODE_DIR / "ansible_secret.py"),
            "-i",
            str(inventory_file),
            str(self._workdir / "collect_host_info.yaml"),
        ]

        stdout_file = self._inventory_dir / "ansible.stdout"
        stderr_file = self._inventory_dir / "ansible.stderr"

        with stdout_file.open(mode="w", encoding="utf-8") as stdout, stderr_file.open(
            mode="w", encoding="utf-8"
        ) as stderr:
            ansible_process = subprocess.Popen(
                ansible_command,  # noqa: S603
                env=get_env_with_venv_path(venv="2.9"),
                stdout=stdout,
                stderr=stderr,
            )

            exit_code = ansible_process.wait()

        if exit_code != 0:
            print(f"Playbook execution failed with exit code {exit_code}")
            sys.exit(exit_code)

        print("Hosts hardware information gathered successfully")
