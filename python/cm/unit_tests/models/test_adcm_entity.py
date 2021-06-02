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


from django.test import TestCase

import cm.models as models
from cm.unit_tests import utils


class ADCMEntityAgendaTest(TestCase):
    """Tests for `cm.models.ADCMEntity` lock-related methods"""

    def setUp(self):
        self.hierarchy = utils.generate_hierarchy()

    def test_is_locked__false(self):
        for obj in self.hierarchy.values():
            self.assertFalse(obj.is_locked)

            for item in obj.agenda.all():
                self.assertFalse(item, 'No locks expected')

    def test_is_locked__true(self):
        lock = utils.gen_agenda_item()
        for obj in self.hierarchy.values():
            obj.add_to_agenda(lock)
            self.assertTrue(obj.is_locked)

    def test_is_locked__deleted(self):
        lock = utils.gen_agenda_item()
        for obj in self.hierarchy.values():
            obj.add_to_agenda(lock)

        lock.delete()
        for obj in self.hierarchy.values():
            self.assertFalse(obj.is_locked)

    def test_add_to_agenda__none(self):
        lock = None
        for obj in self.hierarchy.values():
            obj.add_to_agenda(lock)
            self.assertFalse(obj.is_locked)

    def test_add_to_agenda__deleted(self):
        lock = models.AgendaItem(name=None, reason='unsaved')
        for obj in self.hierarchy.values():
            obj.add_to_agenda(lock)
            self.assertFalse(obj.is_locked)

    def test_add_to_agenda(self):
        lock = utils.gen_agenda_item()
        for obj in self.hierarchy.values():
            obj.add_to_agenda(lock)
            self.assertTrue(obj.is_locked)
            locks = obj.agenda.all()
            self.assertEqual(len(locks), 1)
            self.assertEqual(locks[0].pk, lock.pk)

    def test_remove_from_agenda__none(self):
        nolock = None
        lock = utils.gen_agenda_item()
        for obj in self.hierarchy.values():
            obj.add_to_agenda(lock)
            obj.remove_from_agenda(nolock)
            self.assertTrue(obj.is_locked)

    def test_remove_from_agenda__deleted(self):
        nolock = models.AgendaItem(name=None, reason='unsaved')
        lock = utils.gen_agenda_item()
        for obj in self.hierarchy.values():
            obj.add_to_agenda(lock)
            obj.remove_from_agenda(nolock)
            self.assertTrue(obj.is_locked)
