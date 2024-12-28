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

from importlib import import_module
from typing import Any

from cm.errors import raise_adcm_ex
from cm.models import ADCMEntity, Bundle, HostComponent, ProductCategory
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User as AuthUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.models import (
    CASCADE,
    SET_NULL,
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKey,
    Index,
    JSONField,
    ManyToManyField,
    Model,
    PositiveIntegerField,
    SmallIntegerField,
    TextChoices,
    TextField,
    UniqueConstraint,
)
from django.db.transaction import atomic
from guardian.models import GroupObjectPermission
from guardian.shortcuts import get_perms_for_model

from rbac.utils import get_query_tuple_str


class ObjectType(TextChoices):
    CLUSTER = "cluster", "cluster"
    SERVICE = "service", "service"
    COMPONENT = "component", "component"
    PROVIDER = "provider", "provider"
    HOST = "host", "host"


class OriginType(TextChoices):
    LOCAL = "local", "local"
    LDAP = "ldap", "ldap"


class RoleTypes(TextChoices):
    BUSINESS = "business", "business"
    ROLE = "role", "role"
    HIDDEN = "hidden", "hidden"


class User(AuthUser):
    profile = JSONField(default=str)
    built_in = BooleanField(default=False, null=False)
    failed_login_attempts = SmallIntegerField(default=0)
    blocked_at = DateTimeField(null=True)
    last_failed_login_at = DateTimeField(null=True)
    type = CharField(max_length=1000, choices=OriginType, null=False, default=OriginType.LOCAL)

    @property
    def name(self):
        return self.username


class Group(AuthGroup):
    description = CharField(max_length=1000, default="")
    built_in = BooleanField(default=False, null=False)
    type = CharField(max_length=1000, choices=OriginType, null=False, default=OriginType.LOCAL)

    # works as `name` field because `name` field now contains name and type
    # to bypass unique constraint on `AuthGroup` base table
    display_name = CharField(max_length=1000, null=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["display_name", "type"], name="unique_display_name_type"),
        ]

    def name_to_display(self):
        return self.display_name


class Role(Model):
    name = CharField(max_length=1000)
    description = TextField(blank=True)
    display_name = CharField(max_length=1000, null=False, default="")
    child = ManyToManyField("self", symmetrical=False, blank=True)
    permissions = ManyToManyField(Permission, blank=True)
    module_name = CharField(max_length=1000)
    class_name = CharField(max_length=1000)
    init_params = JSONField(default=dict)
    bundle = ForeignKey(Bundle, on_delete=CASCADE, null=True, default=None)
    built_in = BooleanField(default=True, null=False)
    type = CharField(max_length=1000, choices=RoleTypes, null=False, default=RoleTypes.ROLE)
    category = ManyToManyField(ProductCategory)
    any_category = BooleanField(default=False)
    # should be a list of `ObjectType` strings
    parametrized_by_type = JSONField(default=list, null=False)
    __obj__ = None

    class Meta:
        constraints = [
            UniqueConstraint(fields=["name", "built_in"], name="unique_name"),
            UniqueConstraint(fields=["display_name", "built_in"], name="unique_display_name"),
        ]
        indexes = [
            Index(fields=["name", "display_name"]),
        ]

    def get_role_obj(self) -> Any | None:
        try:
            role_module = import_module(name=self.module_name)
            try:
                role_class = getattr(role_module, self.class_name)

                return role_class(**dict(self.init_params))
            except AttributeError:
                raise_adcm_ex(
                    code="ROLE_CLASS_ERROR",
                    msg=f'No class named "{self.class_name}" in module "{self.module_name}"',
                )
        except ModuleNotFoundError:
            raise_adcm_ex(code="ROLE_MODULE_ERROR", msg=f'No module named "{self.module_name}"')

        return None

    def filter(self):
        if self.__obj__ is None:
            self.__obj__ = self.get_role_obj()

        return self.__obj__.filter()

    def apply(self, policy: "Policy", obj=None) -> None:
        if self.__obj__ is None:
            self.__obj__ = self.get_role_obj()

        self.__obj__.apply(policy=policy, role=self, param_obj=obj)

    def get_permissions(self, role: "Role" = None):
        if role is None:
            role = self

        role_list = Role.objects.raw(
            raw_query="""
                WITH RECURSIVE role_ids AS (
                    SELECT id FROM rbac_role WHERE id = %s
                    UNION SELECT role_child.to_role_id FROM role_ids AS tmp
                    INNER JOIN rbac_role_child AS role_child ON role_child.from_role_id = tmp.id
                ) SELECT id FROM role_ids;
            """,
            params=[role.id],
        )
        return list(Permission.objects.filter(role__in=role_list).distinct())


class RoleMigration(Model):
    version = PositiveIntegerField(primary_key=True)
    date = DateTimeField(auto_now=True)


class PolicyObject(Model):
    content_type = ForeignKey(ContentType, on_delete=CASCADE)
    object_id = PositiveIntegerField()
    object = GenericForeignKey("content_type", "object_id")

    class Meta:
        constraints = [UniqueConstraint(fields=["content_type", "object_id"], name="unique_policy_object")]


class PolicyPermission(Model):
    user = ForeignKey(User, on_delete=CASCADE, null=True, default=None)
    group = ForeignKey(Group, on_delete=CASCADE, null=True, default=None)
    permission = ForeignKey(Permission, on_delete=CASCADE, null=True, default=None)


class Policy(Model):
    name = CharField(max_length=1000, unique=True)
    description = TextField(blank=True)
    role = ForeignKey(Role, on_delete=SET_NULL, null=True)
    object = ManyToManyField(PolicyObject, blank=True)
    built_in = BooleanField(default=True)
    group = ManyToManyField(Group)
    model_perm = ManyToManyField(PolicyPermission, blank=True)
    group_object_perm = ManyToManyField(GroupObjectPermission, blank=True)

    def remove_permissions(self, keep_objects: dict | None = None):
        # Placeholder in some places not used because we need to support Postgres and SQLite and I didn't find a way
        # to use placeholder for list of multiple values for SQLite so used string formatting
        group_pks = self.group.values_list("pk", flat=True)

        cursor = connection.cursor()
        with atomic():
            cursor.execute(
                """
                    SELECT policypermission_id FROM rbac_policy_model_perm WHERE (
                        SELECT COUNT(DISTINCT policy_id) FROM rbac_policy_model_perm WHERE policy_id = %s
                    ) = 1 AND policy_id = %s;
                """,
                [self.pk, self.pk],
            )
            permission_ids_to_delete = {item[0] for item in cursor.fetchall()}
            if permission_ids_to_delete:
                cursor.execute(
                    f"""
                        SELECT policypermission_id FROM rbac_policy_model_perm 
                        WHERE policypermission_id in {get_query_tuple_str(tuple_items=permission_ids_to_delete)} 
                        AND policy_id != {self.pk};
                    """  # noqa: S608, W291
                )

                permission_ids_to_keep = {item[0] for item in cursor.fetchall()}
                if permission_ids_to_keep:
                    permission_ids_to_delete = tuple(permission_ids_to_delete - permission_ids_to_keep)
                else:
                    permission_ids_to_delete = tuple(permission_ids_to_delete)

            if permission_ids_to_delete:
                permission_ids_to_delete_str = get_query_tuple_str(tuple_items=permission_ids_to_delete)

                if group_pks:
                    cursor.execute(
                        f"""
                            DELETE FROM auth_group_permissions WHERE permission_id IN (
                                SELECT permission_id FROM rbac_policypermission WHERE group_id IS NOT NULL 
                                AND id IN {permission_ids_to_delete_str}
                            ) AND group_id IN {get_query_tuple_str(tuple_items=tuple(group_pks))};
                        """,  # noqa: S608, W291
                    )

                cursor.execute(
                    """
                        DELETE FROM rbac_policy_model_perm WHERE policy_id = %s;
                    """,
                    [self.pk],
                )

                cursor.execute(
                    f"""
                        DELETE FROM rbac_policypermission WHERE 
                        (user_id IS NOT NULL OR group_id IS NOT NULL) AND id 
                        IN {get_query_tuple_str(tuple_items=permission_ids_to_delete)};
                    """,  # noqa: S608, W291
                )

            cursor.execute(
                """
                    SELECT groupobjectpermission_id FROM rbac_policy_group_object_perm WHERE (
                        SELECT COUNT(DISTINCT policy_id) FROM rbac_policy_group_object_perm WHERE policy_id = %s
                    ) = 1 AND policy_id = %s;
                """,
                [self.pk, self.pk],
            )
            groupobj_permission_ids_to_delete = {item[0] for item in cursor.fetchall()}
            if groupobj_permission_ids_to_delete:
                keep_group_object_permission_ids = set()
                if keep_objects is not None:
                    for model, ids in keep_objects.items():
                        group_object_permission_ids = self.group_object_perm.filter(
                            object_pk__in=ids,
                            content_type=ContentType.objects.get_for_model(model),
                            group_id__in=group_pks,
                            permission__in=get_perms_for_model(model),
                        ).values_list("id", flat=True)
                        keep_group_object_permission_ids |= set(group_object_permission_ids)

                cursor.execute(
                    f"""
                        SELECT groupobjectpermission_id FROM rbac_policy_group_object_perm 
                        WHERE groupobjectpermission_id 
                        in {get_query_tuple_str(tuple_items=groupobj_permission_ids_to_delete)}
                        AND policy_id != {self.pk};
                    """  # noqa: S608, W291
                )

                groupobj_permission_ids_to_keep = {item[0] for item in cursor.fetchall()}
                groupobj_permission_ids_to_keep |= keep_group_object_permission_ids
                if groupobj_permission_ids_to_keep:
                    groupobj_permission_ids_to_delete = tuple(
                        groupobj_permission_ids_to_delete - groupobj_permission_ids_to_keep
                    )
                else:
                    groupobj_permission_ids_to_delete = tuple(groupobj_permission_ids_to_delete)

            if groupobj_permission_ids_to_delete:
                groupobj_permission_ids_to_delete_str = get_query_tuple_str(
                    tuple_items=groupobj_permission_ids_to_delete
                )

                cursor.execute(
                    f"""
                        DELETE FROM rbac_policy_group_object_perm WHERE groupobjectpermission_id 
                        IN {groupobj_permission_ids_to_delete_str};
                    """,  # noqa: S608, W291
                )

                cursor.execute(
                    f"DELETE FROM guardian_groupobjectpermission WHERE id IN {groupobj_permission_ids_to_delete_str};",  # noqa: S608, W291
                )

    def add_object(self, obj) -> None:
        policy_object = PolicyObject(object=obj)
        policy_object.save()

        self.object.add(policy_object)

    def get_objects(self, param_obj=None):
        if param_obj is not None:
            return [param_obj]

        obj_list = []
        for obj in self.object.order_by("id"):
            obj_list.append(obj.object)

        return obj_list

    def filter(self):
        return self.role.filter()

    def delete(self, using=None, keep_parents=False):
        self.remove_permissions()

        return super().delete(using=using, keep_parents=keep_parents)

    @atomic
    def apply_without_deletion(self):
        self.role.apply(policy=self)

    @atomic
    def apply(self, keep_objects: dict | None = None):
        self.remove_permissions(keep_objects=keep_objects)
        self.role.apply(policy=self)


def get_objects_for_policy(obj: ADCMEntity) -> dict[ADCMEntity, ContentType]:
    obj_type_map = {}
    obj_type = obj.prototype.type if hasattr(obj, "prototype") else None

    if obj_type == "component":
        object_list = [obj, obj.service, obj.cluster]
    elif obj_type == "service":
        object_list = [obj, obj.cluster]
    elif obj_type == "host":
        if obj.cluster:
            object_list = [obj, obj.provider, obj.cluster]

            for hostcomponent in HostComponent.objects.filter(cluster=obj.cluster, host=obj):
                object_list.append(hostcomponent.service)
                object_list.append(hostcomponent.component)
        else:
            object_list = [obj, obj.provider]
    else:
        object_list = [obj]

    for policy_object in object_list:
        obj_type_map[policy_object] = ContentType.objects.get_for_model(model=policy_object)

    return obj_type_map


def re_apply_object_policy(apply_object, keep_objects: dict | None = None):
    obj_type_map = get_objects_for_policy(obj=apply_object)
    for obj, content_type in obj_type_map.items():
        for policy in Policy.objects.filter(object__object_id=obj.id, object__content_type=content_type):
            policy.apply(keep_objects=keep_objects)


RBAC_MODEL_MAP: dict[str, type[User | Group | Role | Policy]] = {
    "user": User,
    "users": User,
    "group": Group,
    "groups": Group,
    "role": Role,
    "roles": Role,
    "policy": Policy,
    "policies": Policy,
}


def get_rbac_model_by_type(rbac_type: str) -> type[User | Group | Role | Policy]:
    return RBAC_MODEL_MAP[rbac_type]
