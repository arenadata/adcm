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

from django.contrib.auth.models import Group as AuthGroup
from rbac.models import Group, OriginType

from adcm.tests.base import BaseTestCase


class GroupTestCase(BaseTestCase):
    def test_group_creation_blank(self):
        with self.assertRaisesRegex(
            RuntimeError, r"Check regex. Data: ", msg="group creation with no args is not allowed"
        ):
            Group.objects.create()

    def test_group_creation_deletion(self):
        for create_args, expected in self.data:
            group = Group.objects.create(**create_args)
            group_pk = group.pk
            base_group_pk = group.group_ptr_id

            self.assertTrue(int(base_group_pk))

            for attr, expected_value in expected.items():
                actual_value = getattr(group, attr)
                self.assertEqual(
                    actual_value,
                    expected_value,
                    f"{group}: wrong {attr} (`{actual_value}`," f" expected: `{expected_value}`)",
                )

            group.delete()

            self.assertFalse(Group.objects.filter(pk=group_pk).first())
            self.assertFalse(AuthGroup.objects.filter(pk=base_group_pk).first())

    def test_group_name_type_mutation(self):
        """test for pre_save signal"""
        group = Group.objects.create(name="test_group_name")
        auth_group = AuthGroup.objects.get(pk=group.group_ptr_id)

        name = "another_test_group_name"
        group.name = name
        group.save()

        group.refresh_from_db()
        auth_group.refresh_from_db()

        self.assertEqual(group.type, OriginType.LOCAL.value)
        self.assertEqual(group.name, auth_group.name, f"{name} [{OriginType.LOCAL.value}]")
        self.assertEqual(group.display_name, name)

        group.type = OriginType.LDAP
        group.save()

        group.refresh_from_db()
        auth_group.refresh_from_db()

        self.assertEqual(group.type, OriginType.LDAP.value)
        self.assertEqual(group.name, auth_group.name, f"{name} [{OriginType.LDAP.value}]")
        self.assertEqual(group.display_name, name)

    data = [
        (
            {
                "name": "test_group_name",
                "description": "test_group_description",
                "type": OriginType.LOCAL,
            },
            {
                "name": f"test_group_name [{OriginType.LOCAL.value}]",
                "description": "test_group_description",
                "type": OriginType.LOCAL,
                "display_name": "test_group_name",
            },
        ),
        (
            {
                "name": "test_group_name_2",
            },
            {
                "name": f"test_group_name_2 [{OriginType.LOCAL.value}]",
                "description": None,
                "type": OriginType.LOCAL,
                "display_name": "test_group_name_2",
            },
        ),
        (
            {
                "name": "test_group_name3",
                "description": "test_group_description3",
                "type": OriginType.LDAP,
            },
            {
                "name": f"test_group_name3 [{OriginType.LDAP.value}]",
                "description": "test_group_description3",
                "type": OriginType.LDAP,
                "display_name": "test_group_name3",
                "built_in": False,
            },
        ),
    ]
