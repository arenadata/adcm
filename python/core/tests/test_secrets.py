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
from tempfile import gettempdir
from unittest import TestCase
import json

from core import secrets


class TestSecrets(TestCase):
    def test_fs_secrets(self):
        path = Path(gettempdir()) / "secretsfile.json"

        with self.assertRaises(secrets.SecretsError):
            secrets.FSSecretsProvider(path=path).get()

        with path.open(mode="w") as f:
            json.dump(secrets.new(), f)

        fs_provider = secrets.FSSecretsProvider(path=path)
        secrets_ = fs_provider.get()

        self.assertIsInstance(secrets_, secrets.ADCMSecrets)
        self.assertIsInstance(secrets_.django.secret_key, str)
        self.assertIsInstance(secrets_.ansible.ansible_vault, str)
        self.assertIsInstance(secrets_.backend.status_service_token, str)
        self.assertIsInstance(secrets_.status_service.adcm_token, str)

        path.unlink()
