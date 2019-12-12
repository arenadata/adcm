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

import json

from django.test import TestCase
from django.utils import timezone

from cm.models import ObjectConfig, ConfigLog, ADCM, Prototype, Bundle


class TestInventory(TestCase):

    def setUp(self):
        self.bundle = Bundle.objects.create(**{
            'name': 'ADB',
            'version': '2.5',
            'version_order': 4,
            'edition': 'community',
            'license': 'absent',
            'license_path': None,
            'license_hash': None,
            'hash': '2232f33c6259d44c23046fce4382f16c450f8ba5',
            'description': '',
            'date': timezone.now()
        })
        self.prototype = Prototype.objects.create(**{
            'bundle': self.bundle,
            'type': 'cluster',
            'name': 'ADB',
            'display_name': 'ADB',
            'version': '2.5',
            'version_order': 11,
            'required': False,
            'shared': False,
            'adcm_min_version': None,
            'monitoring': 'active',
            'description': ''
        })
        self.object_config = ObjectConfig.objects.create(**{
            'current': 1,
            'previous': 1
        })
        self.config_log = ConfigLog.objects.create(**{
            'obj_ref': self.object_config,
            'config': json.dumps(
                {
                    "global": {
                        "send_stats": True,
                        "adcm_url": None
                    },
                    "google_oauth": {
                        "client_id": None,
                        "secret": None,
                        "whitelisted_domains": None
                    }
                }),
            'attr': '{}',
            'date': timezone.now(),
            'description': ''
        })
        self.adcm = ADCM.objects.create(**{
            'prototype': self.prototype,
            'name': 'ADCM',
            'config': self.object_config,
            'state': 'created',
            'stack': '',
            'issue': ''
        })

    def test_process_config(self):
        pass

    def test_get_obj_config(self):
        pass
