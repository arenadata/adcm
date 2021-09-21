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

from uuid import uuid4

from django.test import TestCase

from cm import models
from cm.errors import AdcmEx
from cm.unit_tests import utils


class MessageTemplateTest(TestCase):
    """Tests for `cm.models.MessageTemplate` methods"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        utils.gen_adcm()

    def test_unknown_message(self):
        with self.assertRaises(AdcmEx) as ex:
            models.MessageTemplate.get_message_from_template('unknown')
        self.assertEqual(ex.exception.args[0], 'NO_MODEL_ERROR_CODE')

    def test_bad_template__no_placeholder(self):
        tpl = models.MessageTemplate.obj.create(
            name=uuid4().hex,
            template={
                'message': 'Some message',
            },
        )
        with self.assertRaises(AdcmEx) as ex:
            models.MessageTemplate.get_message_from_template(tpl.name)
        self.assertIn('KeyError', ex.exception.msg)
        self.assertIn('placeholder', ex.exception.msg)

    def test_bad_template__no_type(self):
        tpl = models.MessageTemplate.obj.create(
            name=uuid4().hex,
            template={'message': 'Some message ${data}', 'placeholder': {'data': {}}},
        )
        with self.assertRaises(AdcmEx) as ex:
            models.MessageTemplate.get_message_from_template(tpl.name)
        self.assertIn('KeyError', ex.exception.msg)
        self.assertIn('type', ex.exception.msg)

    def test_bad_template__unknown_type(self):
        tpl = models.MessageTemplate.obj.create(
            name=uuid4().hex,
            template={
                'message': 'Some message ${data}',
                'placeholder': {'data': {'type': 'foobar'}},
            },
        )
        with self.assertRaises(AdcmEx) as ex:
            models.MessageTemplate.get_message_from_template(tpl.name)
        self.assertIn('KeyError', ex.exception.msg)
        self.assertIn('foobar', ex.exception.msg)

    def test_bad_template__bad_placeholder(self):
        tpl = models.MessageTemplate.obj.create(
            name=uuid4().hex, template={'message': 'Some message ${cluster}', 'placeholder': []}
        )
        with self.assertRaises(AdcmEx) as ex:
            models.MessageTemplate.get_message_from_template(tpl.name)
        self.assertIn('AttributeError', ex.exception.msg)
        self.assertIn('list', ex.exception.msg)

    def test_bad_template__bad_args(self):
        name = models.MessageTemplate.KnownNames.LockedByAction.value
        with self.assertRaises(AdcmEx) as ex:
            models.MessageTemplate.get_message_from_template(name)
        print(ex.exception)
        self.assertIn('AssertionError', ex.exception.msg)
