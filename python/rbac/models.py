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

import importlib
import re

from cm.errors import raise_adcm_ex
from cm.models import ADCMEntity, Bundle, HostComponent, ProductCategory
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User as AuthUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
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
from django.db.models.signals import pre_save
from django.db.transaction import atomic
from django.dispatch import receiver
from guardian.models import GroupObjectPermission, UserObjectPermission
from rest_framework.exceptions import ValidationError


class ObjectType(TextChoices):
    CLUSTER = "cluster", "cluster"
    SERVICE = "service", "service"
    COMPONENT = "component", "component"
    PROVIDER = "provider", "provider"
    HOST = "host", "host"


def validate_object_type(value):
    if not isinstance(value, list):
        raise ValidationError("Not a valid list.")

    if not all(v in ObjectType.values for v in value):
        raise ValidationError("Not a valid object type.")


class OriginType(TextChoices):
    LOCAL = "local", "local"
    LDAP = "ldap", "ldap"


class User(AuthUser):
    """
    Beware the Multi-table inheritance
    Original User model extended with profile
    """

    profile = JSONField(default=str)
    built_in = BooleanField(default=False, null=False)
    failed_login_attempts = SmallIntegerField(default=0)
    blocked_at = DateTimeField(null=True)

    def delete(self, using=None, keep_parents=False):
        self.is_active = False
        self.save()

    type = CharField(max_length=1000, choices=OriginType.choices, null=False, default=OriginType.LOCAL)

    @property
    def name(self):
        return self.username


class Group(AuthGroup):
    """
    Beware the Multi-table inheritance
    Original Group model extended with description field
    """

    description = CharField(max_length=1000, null=True)
    built_in = BooleanField(default=False, null=False)
    type = CharField(max_length=1000, choices=OriginType.choices, null=False, default=OriginType.LOCAL)
    # works as `name` field because `name` field now contains name and type
    # to bypass unique constraint on `AuthGroup` base table
    display_name = CharField(max_length=1000, null=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["display_name", "type"], name="unique_display_name_type"),
        ]

    def name_to_display(self):
        return self.display_name


BASE_GROUP_NAME_PATTERN = re.compile(rf'(?P<base_name>.*?)(?: \[(?:{"|".join(OriginType.values)})\]|$)')


@receiver(pre_save, sender=Group)
def handle_name_type_display_name(sender, instance, **kwargs):  # pylint: disable=unused-argument
    if kwargs["raw"]:
        return

    match = BASE_GROUP_NAME_PATTERN.match(instance.name)
    if match and match.group("base_name"):
        instance.name = f"{match.group('base_name')} [{instance.type}]"
        instance.display_name = match.group("base_name")
    else:
        raise_adcm_ex(code="GROUP_CONFLICT", msg=f"Check regex. Data: `{instance.name}`")


class RoleTypes(TextChoices):
    BUSINESS = "business", "business"
    ROLE = "role", "role"
    HIDDEN = "hidden", "hidden"


class Role(Model):  # pylint: disable=too-many-instance-attributes
    """
    Role is a list of Django permissions.
    Role can be assigned to user or to group of users
    Also Role can have children and so produce acyclic graph of linked roles
    """

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
    type = CharField(max_length=1000, choices=RoleTypes.choices, null=False, default=RoleTypes.ROLE)
    category = ManyToManyField(ProductCategory)
    any_category = BooleanField(default=False)
    parametrized_by_type = JSONField(default=list, null=False, validators=[validate_object_type])
    __obj__ = None

    class Meta:
        constraints = [
            UniqueConstraint(fields=["name", "built_in"], name="unique_name"),
            UniqueConstraint(fields=["display_name", "built_in"], name="unique_display_name"),
        ]
        indexes = [
            Index(fields=["name", "display_name"]),
        ]

    def get_role_obj(self):
        """Returns object with related role based on classes from roles.py"""

        try:
            role_module = importlib.import_module(self.module_name)
        except ModuleNotFoundError:
            raise_adcm_ex("ROLE_MODULE_ERROR", f'No module named "{self.module_name}"')

        try:
            role_class = getattr(role_module, self.class_name)
        except AttributeError:
            msg = f'No class named "{self.class_name}" in module "{self.module_name}"'
            raise_adcm_ex("ROLE_CLASS_ERROR", msg)

        return role_class(**self.init_params)  # pylint: disable=E1134

    def filter(self):
        """filter out objects suitable for role"""

        if self.__obj__ is None:
            self.__obj__ = self.get_role_obj()

        return self.__obj__.filter()

    def apply(self, policy: "Policy", user: User, group: Group, obj=None):
        """apply policy to user and/or group"""

        if self.__obj__ is None:
            self.__obj__ = self.get_role_obj()

        return self.__obj__.apply(policy, self, user, group, obj)

    def get_permissions(self, role: "Role" = None):
        """Recursively get permissions of role and all her children"""

        if role is None:
            role = self

        # the raw query was added to avoid many SQL queries
        role_list = Role.objects.raw(
            """
                with recursive role_ids as (
                    select id from rbac_role where id = %s
                    union
                    select role_child.to_role_id from role_ids as tmp
                    inner join rbac_role_child as role_child on role_child.from_role_id = tmp.id
                ) select id from role_ids;
            """,
            params=[role.id],
        )
        perm_list = list(Permission.objects.filter(role__in=role_list).distinct())

        return perm_list


class RoleMigration(Model):
    """Keep version of last role upgrade"""

    version = PositiveIntegerField(primary_key=True)
    date = DateTimeField(auto_now=True)


class PolicyObject(Model):
    """Reference to any model for Policy"""

    content_type = ForeignKey(ContentType, on_delete=CASCADE)
    object_id = PositiveIntegerField()
    object = GenericForeignKey("content_type", "object_id")

    class Meta:
        constraints = [UniqueConstraint(fields=["content_type", "object_id"], name="unique_policy_object")]


class PolicyPermission(Model):
    """Reference to Policy model level Permissions"""

    user = ForeignKey(User, on_delete=CASCADE, null=True, default=None)
    group = ForeignKey(Group, on_delete=CASCADE, null=True, default=None)
    permission = ForeignKey(Permission, on_delete=CASCADE, null=True, default=None)


class Policy(Model):
    """Policy connect role, users and (maybe) objects"""

    name = CharField(max_length=1000, unique=True)
    description = TextField(blank=True)
    role = ForeignKey(Role, on_delete=SET_NULL, null=True)
    object = ManyToManyField(PolicyObject, blank=True)
    built_in = BooleanField(default=True)
    user = ManyToManyField(User, blank=True)
    group = ManyToManyField(Group, blank=True)
    model_perm = ManyToManyField(PolicyPermission, blank=True)
    user_object_perm = ManyToManyField(UserObjectPermission, blank=True)
    group_object_perm = ManyToManyField(GroupObjectPermission, blank=True)

    def remove_permissions(self):
        with atomic():
            for policy_permission in self.model_perm.order_by("id"):
                if policy_permission.policy_set.count() <= 1:
                    if policy_permission.user:
                        policy_permission.user.user_permissions.remove(policy_permission.permission)

                    if policy_permission.group:
                        policy_permission.group.permissions.remove(policy_permission.permission)

                policy_permission.policy_set.remove(self)

            for uop in self.user_object_perm.order_by("id"):
                if uop.policy_set.count() <= 1:
                    uop.delete()

            for gop in self.group_object_perm.order_by("id"):
                if gop.policy_set.count() <= 1:
                    gop.delete()

    def add_object(self, obj):
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

        return super().delete(using, keep_parents)

    @atomic
    def apply_without_deletion(self):
        for user in self.user.order_by("id"):
            self.role.apply(self, user, None)

        for group in self.group.all():
            self.role.apply(self, None, group=group)

    @atomic
    def apply(self):
        self.remove_permissions()
        for user in self.user.all():
            self.role.apply(self, user, None)

        for group in self.group.all():
            self.role.apply(self, None, group=group)


def get_objects_for_policy(obj: ADCMEntity) -> dict[ADCMEntity, ContentType]:
    obj_type_map = {}
    obj_type = obj.prototype.type

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
        obj_type_map[policy_object] = ContentType.objects.get_for_model(policy_object)

    return obj_type_map


def re_apply_object_policy(apply_object):
    """
    This function search for polices linked with specified object and re apply them
    """

    obj_type_map = get_objects_for_policy(apply_object)
    for obj, content_type in obj_type_map.items():
        for policy in Policy.objects.filter(object__object_id=obj.id, object__content_type=content_type):
            policy.apply()


def re_apply_all_polices():
    """
    This function re apply all polices
    """

    for policy in Policy.objects.all():
        policy.apply()
