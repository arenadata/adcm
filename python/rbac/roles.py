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

"""RBAC Role classes"""

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from guardian.models import UserObjectPermission, GroupObjectPermission
from adwp_base.errors import raise_AdwpEx as err
from rbac.models import Policy, PolicyPermission, Role, User, Group, Permission
from cm.models import (
    Action,
    ClusterObject,
    ServiceComponent,
    Host,
    HostComponent,
    get_model_by_type,
    TaskLog,
    JobLog,
    LogStorage,
)


class AbstractRole:
    """Abstract class for custom Role handlers"""

    class Meta:
        abstract = True

    def __init__(self, **kwargs):
        self.params = kwargs

    def apply(self, policy: Policy, role: Role, user: User, group: Group, param_obj=None):
        """
        This method should apply Role to User and/or Group.
        Generaly this means that you should assign permissions from Role to User and/or Group
        and save links to these permissions in Policy model.
        If Role is parametrized_by_type than parametrized objects should be obtained from
        Policy.object field.
        Optional parameter param_obj can be used to specify the object in complex cases
        (see ParentRole below)
        """
        raise NotImplementedError("You must provide apply method")


class ModelRole(AbstractRole):
    """This Role apply Django model level permissions"""

    def apply(self, policy: Policy, role: Role, user: User, group: Group, param_obj=None):
        """Apply Role to User and/or Group"""
        for perm in role.get_permissions():
            if group is not None:
                group.permissions.add(perm)
                pp = PolicyPermission(policy=policy, group=group, permission=perm)
                pp.save()
                policy.model_perm.add(pp)
            if user is not None:
                user.user_permissions.add(perm)
                pp = PolicyPermission(policy=policy, user=user, permission=perm)
                pp.save()
                policy.model_perm.add(pp)


def assign_user_or_group_perm(user, group, policy, perm, obj):
    if user is not None:
        uop = UserObjectPermission.objects.assign_perm(perm, user, obj)
        policy.user_object_perm.add(uop)
    if group is not None:
        gop = GroupObjectPermission.objects.assign_perm(perm, group, obj)
        policy.group_object_perm.add(gop)


class ObjectRole(AbstractRole):
    """This Role apply django-guardian object level permissions"""

    def filter(self):
        if 'model' not in self.params:
            return None
        try:
            model = apps.get_model(self.params['app_name'], self.params['model'])
        except LookupError as e:
            err('ROLE_FILTER_ERROR', str(e))
        return model.objects.filter(**self.params['filter'])

    def apply(self, policy: Policy, role: Role, user: User, group: Group, param_obj=None):
        """Apply Role to User and/or Group"""
        for obj in policy.get_objects(param_obj):
            for perm in role.get_permissions():
                assign_user_or_group_perm(user, group, policy, perm, obj)


class ActionRole(AbstractRole):
    """This Role apply permissions to run ADCM action"""

    def filter(self):
        if 'model' not in self.params:
            return None
        try:
            model = apps.get_model(self.params['app_name'], self.params['model'])
        except LookupError as e:
            err('ROLE_FILTER_ERROR', str(e))
        return model.objects.filter(**self.params['filter'])

    def apply(self, policy: Policy, role: Role, user: User, group: Group = None, param_obj=None):
        """Apply Role to User and/or Group"""
        action = Action.obj.get(id=self.params['action_id'])
        assign_user_or_group_perm(user, group, policy, get_perm_for_model(Action), action)
        for obj in policy.get_objects(param_obj):
            model = get_model_by_type(obj.prototype.type)
            ct = ContentType.objects.get_for_model(model)
            run_action, _ = Permission.objects.get_or_create(
                content_type=ct, codename=f'run_action_{action.display_name}'
            )
            assign_user_or_group_perm(user, group, policy, run_action, obj)


def get_perm_for_model(model):
    ct = ContentType.objects.get_for_model(model)
    codename = f'view_{model.__name__.lower()}'
    perm, _ = Permission.objects.get_or_create(content_type=ct, codename=codename)
    return perm


def apply_jobs(task: TaskLog, policy: Policy, user: User, group: Group = None):
    assign_user_or_group_perm(user, group, policy, get_perm_for_model(TaskLog), task)
    for job in JobLog.objects.filter(task=task):
        assign_user_or_group_perm(user, group, policy, get_perm_for_model(JobLog), job)
        for log in LogStorage.objects.filter(job=job):
            assign_user_or_group_perm(user, group, policy, get_perm_for_model(LogStorage), log)


def re_apply_policy_for_jobs(object, task):
    id_type_dict = {}
    object_model = object.__class__.__name__.lower()
    if object.prototype.type == 'component':
        object_list = [object, object.service, object.cluster]
    elif object.prototype.type == 'service':
        object_list = [object, object.cluster]
    else:
        object_list = [object]
    for obj in object_list:
        id_type_dict[obj] = ContentType.objects.get_for_model(obj)

    for obj, ct in id_type_dict.items():
        for policy in Policy.objects.filter(object__object_id=obj.id, object__content_type=ct):
            for user in policy.user.all():
                try:
                    uop = UserObjectPermission.objects.get(
                        user=user, permission__codename='view_action', object_pk=task.action.pk
                    )
                except UserObjectPermission.DoesNotExist:
                    continue
                if uop in policy.user_object_perm.all() and user.has_perm(
                    f'view_{object_model}', object
                ):
                    apply_jobs(task, policy, user, None)
            for group in policy.group.all():
                try:
                    gop = GroupObjectPermission.objects.get(
                        group=group, permission__codename='view_action', object_pk=task.action.pk
                    )
                except UserObjectPermission.DoesNotExist:
                    continue
                if gop in policy.group_object_perm.all() and group.has_perm(
                    f'view_{object_model}', object
                ):
                    apply_jobs(task, policy, None, group)


class ParentRole(AbstractRole):
    """This Role is used for complex Roles that can include other Roles"""

    def find_and_apply(self, obj, policy, role, user, group=None):
        """Find Role of appropriate type and apply it to specified object"""
        for r in role.child.all():
            if r.class_name not in ('ObjectRole', 'ActionRole'):
                continue
            if obj.prototype.type in r.parametrized_by_type:
                r.apply(policy, user, group, obj)

    def apply(
        self, policy: Policy, role: Role, user: User, group: Group = None, param_obj=None
    ):  # pylint: disable=too-many-branches
        """Apply Role to User and/or Group"""
        for obj in policy.get_objects(param_obj):
            self.find_and_apply(obj, policy, role, user, group)

            if obj.prototype.type == 'cluster':
                for service in ClusterObject.obj.filter(cluster=obj):
                    self.find_and_apply(service, policy, role, user, group)
                    for comp in ServiceComponent.obj.filter(service=service):
                        self.find_and_apply(comp, policy, role, user, group)
                for host in Host.obj.filter(cluster=obj):
                    self.find_and_apply(host, policy, role, user, group)

            elif obj.prototype.type == 'service':
                for comp in ServiceComponent.obj.filter(service=obj):
                    self.find_and_apply(comp, policy, role, user, group)
                for hc in HostComponent.obj.filter(cluster=obj.cluster, service=obj):
                    self.find_and_apply(hc.host, policy, role, user, group)
                self.find_and_apply(obj.cluster, policy, role, user, group)

            elif obj.prototype.type == 'component':
                for hc in HostComponent.obj.filter(
                    cluster=obj.cluster, service=obj.service, component=obj
                ):
                    self.find_and_apply(hc.host, policy, role, user, group)
                self.find_and_apply(obj.cluster, policy, role, user, group)
                self.find_and_apply(obj.service, policy, role, user, group)

            elif obj.prototype.type == 'provider':
                for host in Host.obj.filter(provider=obj):
                    self.find_and_apply(host, policy, role, user, group)

        for r in role.child.all():
            if r.class_name in ('ModelRole', 'ParentRole'):
                r.apply(policy, user, group, param_obj)
