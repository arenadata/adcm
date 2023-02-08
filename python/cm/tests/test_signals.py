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

from unittest.mock import patch

from cm.models import Bundle, Cluster, GroupConfig, Host, Prototype
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import m2m_changed, post_delete, post_save
from rbac.models import User

from adcm.tests.base import BaseTestCase


class SignalsTest(BaseTestCase):
    @patch("cm.signals.model_delete")
    @patch("cm.signals.model_change")
    def test_update_delete_signals(self, model_change, model_delete):
        post_save.connect(model_change, sender=User)
        post_delete.connect(model_delete, sender=User)
        User.objects.create_user("test_user_2", "", "")
        User.objects.filter(username="test_user_2").delete()
        model_change.assert_called_once()
        model_delete.assert_called_once()

    @patch("cm.signals.m2m_change")
    def test_m2m_signals(self, m2m_change):
        m2m_changed.connect(m2m_change, sender=GroupConfig.hosts.through)
        bundle = Bundle.objects.create()
        cluster = Cluster.objects.create(
            prototype=Prototype.objects.create(type="cluster", name="prototype", bundle=bundle)
        )
        group_config = GroupConfig.objects.create(
            object_id=cluster.id, object_type=ContentType.objects.get(model="cluster"), name="group"
        )
        host = Host.objects.create(
            cluster=cluster, prototype=Prototype.objects.create(type="host", name="prototype_2", bundle=bundle)
        )

        group_config.hosts.add(host)

        self.assertEqual(2, m2m_change.call_count)
