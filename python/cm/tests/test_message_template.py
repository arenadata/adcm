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

from cm.errors import AdcmEx
from cm.models import MessageTemplate
from cm.tests.utils import gen_adcm

from adcm.tests.base import BaseTestCase


class MessageTemplateTest(BaseTestCase):
    def setUp(self):
        super().setUp()

        gen_adcm()

    def test_unknown_message(self):
        with self.assertRaises(AdcmEx) as e:
            MessageTemplate.get_message_from_template("unknown")

        self.assertEqual(e.exception.args[0], "NO_MODEL_ERROR_CODE")

    def test_bad_template__no_placeholder(self):
        tpl = MessageTemplate.obj.create(
            name=uuid4().hex,
            template={
                "message": "Some message",
            },
        )
        with self.assertRaises(AdcmEx) as e:
            MessageTemplate.get_message_from_template(tpl.name)

        self.assertIn("KeyError", e.exception.msg)
        self.assertIn("placeholder", e.exception.msg)

    def test_bad_template__no_type(self):
        tpl = MessageTemplate.obj.create(
            name=uuid4().hex,
            template={"message": "Some message ${data}", "placeholder": {"data": {}}},
        )
        with self.assertRaises(AdcmEx) as e:
            MessageTemplate.get_message_from_template(tpl.name)

        self.assertIn("KeyError", e.exception.msg)
        self.assertIn("type", e.exception.msg)

    def test_bad_template__unknown_type(self):
        tpl = MessageTemplate.obj.create(
            name=uuid4().hex,
            template={
                "message": "Some message ${data}",
                "placeholder": {"data": {"type": "foobar"}},
            },
        )
        with self.assertRaises(AdcmEx) as e:
            MessageTemplate.get_message_from_template(tpl.name)

        self.assertIn("KeyError", e.exception.msg)
        self.assertIn("foobar", e.exception.msg)

    def test_bad_template__bad_placeholder(self):
        tpl = MessageTemplate.obj.create(
            name=uuid4().hex,
            template={"message": "Some message ${cluster}", "placeholder": []},
        )
        with self.assertRaises(AdcmEx) as e:
            MessageTemplate.get_message_from_template(tpl.name)

        self.assertIn("AttributeError", e.exception.msg)
        self.assertIn("list", e.exception.msg)

    def test_bad_template__bad_args(self):
        name = MessageTemplate.KnownNames.LOCKED_BY_JOB.value
        with self.assertRaises(AdcmEx) as e:
            MessageTemplate.get_message_from_template(name)

        self.assertIn("AssertionError", e.exception.msg)
