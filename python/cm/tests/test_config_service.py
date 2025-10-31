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

from copy import deepcopy
from pathlib import Path

from adcm.tests.base import BusinessLogicMixin, ParallelReadyTestCase
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.test import TestCase
from infra.services import get_config_service
from init_db import init
from rbac.upgrade.role import init_roles
import core


class TestPrepareNewConfiguration(BusinessLogicMixin, ParallelReadyTestCase, TestCase):
    def setUp(self):
        super().setUp()

        init_roles()
        init()

        self.config_service = get_config_service()

        self.bundle = self.add_bundle(Path(__file__).parent / "bundles" / "cluster_full_config")
        self.cluster = self.add_cluster(bundle=self.bundle, name="with-config")

        self.cluster_owner_info = core.config.ConfigOwner(
            descriptor=CoreObjectDescriptor(id=self.cluster.pk, type=ADCMCoreType.CLUSTER),
            info=core.config.ConfigOwnerObjectInfo(state=self.cluster.state),
        )
        self.cluster_spec, self.cluster_defaults = self.config_service.retrieve_specification(
            owner=self.cluster_owner_info.descriptor
        )

    def test_same_as_default_success(self):
        input_config = core.config.Configuration(
            values=core.config.flat_to_nested(self.cluster_defaults),
            attributes={"/activatable_group": core.config.Attributes(is_active=True)},
        )
        result = self.config_service.prepare_new_configuration(
            new=input_config, previous=input_config, specification=self.cluster_spec, owner=self.cluster_owner_info
        )

        self.assertFalse(result.has_changed)

    def test_encryption_success(self):
        secret_value = "verysecret"
        default_config = core.config.Configuration(
            values=core.config.flat_to_nested(self.cluster_defaults),
            attributes={"/activatable_group": core.config.Attributes(is_active=True)},
        )
        input_config = deepcopy(default_config)
        input_config.values |= {
            "string": secret_value,
            "map": {"key": secret_value},
            "text": secret_value,
            "file": secret_value,
            "secrettext": secret_value,
            "secretmap": {"key": secret_value},
            "secretfile": secret_value,
        }

        result = self.config_service.prepare_new_configuration(
            new=input_config, previous=default_config, specification=self.cluster_spec, owner=self.cluster_owner_info
        )
        encrypted_values = result.encrypted_config.values

        self.assertTrue(result.has_changed)
        self.assertTrue(self.config_service.secrets.is_encrypted(encrypted_values["secrettext"]))
        self.assertTrue(self.config_service.secrets.is_encrypted(encrypted_values["secretmap"]["key"]))
        self.assertTrue(self.config_service.secrets.is_encrypted(encrypted_values["secretfile"]))
        self.assertFalse(self.config_service.secrets.is_encrypted(encrypted_values["string"]))
        self.assertFalse(self.config_service.secrets.is_encrypted(encrypted_values["map"]["key"]))
        self.assertFalse(self.config_service.secrets.is_encrypted(encrypted_values["file"]))
        self.assertFalse(self.config_service.secrets.is_encrypted(encrypted_values["text"]))
        self.assertEqual(self.config_service.secrets.decrypt(encrypted_values["secrettext"]), secret_value)
        self.assertEqual(self.config_service.secrets.decrypt(encrypted_values["secretmap"]["key"]), secret_value)
        self.assertEqual(self.config_service.secrets.decrypt(encrypted_values["secretfile"]), secret_value)
