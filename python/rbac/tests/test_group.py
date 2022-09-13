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

from adcm.tests.base import BaseTestCase
from rbac.models import Group, OriginType


class GroupBaseTestCase(BaseTestCase):
    def test_group_creation_blank(self):
        with self.assertRaisesRegex(
            RuntimeError, r"Check regex. Data: ", msg="group creation with no args is not allowed"
        ):
            Group.objects.create()

    def test_group_creation_deletion(self):
        for create_args, expected in self.data:
            g = Group.objects.create(**create_args)
            g_pk = g.pk
            base_g_pk = g.group_ptr_id

            self.assertTrue(int(base_g_pk))

            for attr, expected_value in expected.items():
                actual_value = getattr(g, attr)
                self.assertEqual(
                    actual_value,
                    expected_value,
                    f"{g}: wrong {attr} (`{actual_value}`," f" expected: `{expected_value}`)",
                )

            g.delete()

            self.assertFalse(Group.objects.filter(pk=g_pk).first())
            self.assertFalse(AuthGroup.objects.filter(pk=base_g_pk).first())

    def test_group_name_type_mutation(self):
        """test for pre_save signal"""
        g = Group.objects.create(name="test_group_name")
        ag = AuthGroup.objects.get(pk=g.group_ptr_id)

        name = "another_test_group_name"
        g.name = name
        g.save()

        g.refresh_from_db()
        ag.refresh_from_db()

        self.assertEqual(g.type, OriginType.Local.value)
        self.assertEqual(g.name, ag.name, f"{name} [{OriginType.Local.value}]")
        self.assertEqual(g.display_name, name)

        g.type = OriginType.LDAP
        g.save()

        g.refresh_from_db()
        ag.refresh_from_db()

        self.assertEqual(g.type, OriginType.LDAP.value)
        self.assertEqual(g.name, ag.name, f"{name} [{OriginType.LDAP.value}]")
        self.assertEqual(g.display_name, name)

    data = [
        (
            {
                "name": "test_group_name",
                "description": "test_group_description",
                "type": OriginType.Local,
            },
            {
                "name": f"test_group_name [{OriginType.Local.value}]",
                "description": "test_group_description",
                "type": OriginType.Local,
                "display_name": "test_group_name",
            },
        ),
        (
            {
                "name": "test_group_name_2",
            },
            {
                "name": f"test_group_name_2 [{OriginType.Local.value}]",
                "description": None,
                "type": OriginType.Local,
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
