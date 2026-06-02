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


from django.test import TestCase as DjangoTestCase
from parameterized import parameterized

from audit.alt.core import (
    AuditConfigurationError,
    NameHalfSplitter,
    NameSplitterSettings,
    OperationNameTemplate,
    build_name_splitter_settings_from_django_models,
)


class TestAuditUtilsWithDB(DjangoTestCase):
    def test_name_splitter_settings(self):
        """
        These settings are crucial for correct work of audit.
        If operation_name_max_len or truncated_message are changed, check
        OperationAuditContext._name_splitter implementation
        """

        settings = build_name_splitter_settings_from_django_models()
        self.assertIsInstance(settings, NameSplitterSettings)
        self.assertEqual(settings.operation_name_max_len, 2000)
        self.assertEqual(settings.truncated_message, "...<truncated>")
        self.assertEqual(settings.delimiter, ", ")


class TestAuditUtils(DjangoTestCase):
    splitter = NameHalfSplitter(NameSplitterSettings(operation_name_max_len=50))

    @parameterized.expand(
        [
            (
                "single name, no changes",
                "[{}] object(s) audited.",
                ("object-name",),
                ["[object-name] object(s) audited."],
                None,
            ),
            (
                "three names, fits in one operation name",
                "[{}] object(s) audited.",
                ("objname1", "objname2", "objname3"),
                ["[objname1, objname2, objname3] object(s) audited."],
                None,
            ),
            (
                "three names, splits in two operation names",
                "[{}] object(s) audited.",
                (f"{'obj'*5}1", f"{'obj'*2}2", f"{'obj'*2}3"),
                [f"[{'obj'*5}1] object(s) audited.", f"[{'obj'*2}2, {'obj'*2}3] object(s) audited."],
                None,
            ),
            (
                "one name, truncated",
                "[{}] object(s) audited.",
                ("very_long_object_name_version_1_edition_2",),
                ["[very_long_objec...<truncated>] object(s) audited."],
                None,
            ),
            (
                "template and truncated_msg are longer than field limit, expect error",
                "[{}] object(s) audited and it's names are stored in ridiculously long operation name.",
                ("objectname",),
                [],
                AuditConfigurationError(
                    "Can't truncate object's name `objectname` to suite operation_name field max length. "
                    "Adjust some of the following: template_len=83, truncated_msg_len=14, operation_name_len=50"
                ),
            ),
        ]
    )
    def test_name_splitter_with_template(
        self,
        _,
        template: str,
        names: tuple[str, ...],
        expected_operation_names: list[str],
        expected_error: Exception | None,
    ):
        name = OperationNameTemplate(names=names, template=template)

        if expected_error is None:
            self.assertListEqual(self.splitter(name), expected_operation_names)
        else:
            with self.assertRaises(type(expected_error)) as err:
                self.splitter(name)
            exception = err.exception
            self.assertEqual(exception.args[0], expected_error.args[0])

    def test_name_splitter_with_raw_operation_name(self):
        """
        If operation_name is passed as a raw string, no checks or truncation takes place.
        Audit can fail with DBError, it is expected behavior
        """

        operation_name = "[object] audited, exceeding operation_name_max_len limit"
        self.assertTrue(len(operation_name) > self.splitter.settings.operation_name_max_len)
        self.assertListEqual(self.splitter(operation_name), [operation_name])
