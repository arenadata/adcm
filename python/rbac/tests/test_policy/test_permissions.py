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


from cm.models import ADCMEntity, ObjectType, Prototype
from core.legacy.rbac.dto import UserCreateDTO
from core.legacy.rbac.operations import add_user_to_groups
from django.contrib.auth.models import Permission
from tests.suites import GenericTestCase

from rbac.models import Group, Policy, User
from rbac.models import Group as RBACGroup
from rbac.roles import Role, assign_group_perm
from rbac.services.policy import policy_create
from rbac.services.user import GroupDB, UserDB, create_new_user


class RemovePermissionsTestCase(GenericTestCase):
    @classmethod
    def create_policy(
        cls,
        role_name: str,
        obj: ADCMEntity,
        group_pk: int | None = None,
    ) -> int:
        policy_name = f"test_policy_{obj.prototype.type}_{obj.pk}_admin"
        role = Role.objects.get(name=role_name)
        policy = policy_create(
            name=policy_name, role=role, group=[Group.objects.get(id=group_pk)] if group_pk else None, object=[obj]
        )
        return policy.pk

    @classmethod
    def get_new_user(cls, username: str, password: str, group_pk: int | None = None) -> User:
        data = UserCreateDTO(
            username=username, password=password, email="", first_name="", last_name="", is_superuser=False
        )
        user_id = create_new_user(data=data, db=UserDB, password_requirements=None)
        if group_pk:
            add_user_to_groups(user_id=user_id, groups=[group_pk], db=GroupDB)

        return User.objects.get(pk=user_id)

    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

        super().setUpTestData()

        cls.new_user_password = "new_user_password"
        cls.new_user_group = Group.objects.create(name="new_group")
        cls.new_user = cls.get_new_user(
            username="new_user", password=cls.new_user_password, group_pk=cls.new_user_group.pk
        )

        bundle_path = cls.base_dir / "python" / "rbac" / "tests" / "bundles" / "test_cluster_for_cluster_admin_role"
        cluster_bundle = cls.uc.upload_bundle(bundle_path)
        cls.cluster = cls.uc.add_cluster(bundle=cluster_bundle, name="Test Cluster")

        bundle_path = cls.base_dir / "python" / "rbac" / "tests" / "bundles" / "provider"
        provider_bundle = cls.uc.upload_bundle(bundle_path)
        cls.provider = cls.uc.add_provider(bundle=provider_bundle, name="Test Provider")
        cls.service_6_proto = Prototype.objects.get(
            bundle=cluster_bundle,
            name="service_6_manual_add",
            type=ObjectType.SERVICE,
        )

        cls.create_policy(role_name="Cluster Administrator", obj=cls.cluster, group_pk=cls.new_user_group.pk)

        cls.policy = Policy.objects.first()
        cls.policy.group.add(RBACGroup.objects.create(name="test_group_1"))

        assign_group_perm(
            policy=cls.policy,
            permission=Permission.objects.filter(codename="add_group")[0],
            obj=Group.objects.create(name="test_group_2"),
        )

    def test_remove_permissions(self):
        model_permission_codenames = {
            policy_permission.permission.codename for policy_permission in self.policy.model_perm.all()
        }
        group_object_permissions = {
            group_object_permission.permission.codename
            for group_object_permission in self.policy.group_object_perm.all()
        }

        self.assertTrue(model_permission_codenames)
        self.assertTrue(group_object_permissions)

        self.policy.remove_permissions()

        self.policy.refresh_from_db()

        model_permission_codenames = {
            policy_permission.permission.codename for policy_permission in self.policy.model_perm.all()
        }
        group_object_permissions = {
            group_object_permission.permission.codename
            for group_object_permission in self.policy.group_object_perm.all()
        }

        self.assertFalse(model_permission_codenames)
        self.assertFalse(group_object_permissions)
