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
from rbac.models import Policy, PolicyPermission, Role, User, Group, Permission, RoleTypes
from cm.models import (
    Action,
    ClusterObject,
    ServiceComponent,
    Host,
    HostComponent,
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
            for perm in role.get_permissions():
                assign_user_or_group_perm(user, group, policy, perm, obj)


class TaskRole(AbstractRole):
    def apply(self, policy, role, user, group, param_obj=None):
        task = TaskLog.obj.get(id=self.params['task_id'])
        for obj in policy.get_objects(param_obj):
            if obj == task.task_object:
                apply_jobs(task, policy, user, group)


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


def get_objects_for_policy(obj):
    obj_type_map = {}
    obj_type = obj.prototype.type
    if obj_type == 'component':
        object_list = [obj, obj.service, obj.cluster]
    elif obj_type == 'service':
        object_list = [obj, obj.cluster]
    elif obj_type == 'host':
        if obj.cluster:
            object_list = [obj, obj.provider, obj.cluster]
            for hc in HostComponent.objects.filter(cluster=obj.cluster, host=obj):
                object_list.append(hc.service)
                object_list.append(hc.component)
        else:
            object_list = [obj, obj.provider]
    else:
        object_list = [obj]
    for policy_object in object_list:
        obj_type_map[policy_object] = ContentType.objects.get_for_model(policy_object)
    return obj_type_map


def re_apply_policy_for_jobs(action_object, task):
    obj_type_map = get_objects_for_policy(action_object)
    object_model = action_object.__class__.__name__.lower()
    task_role, _ = Role.objects.get_or_create(
        name=f'View role for task {task.id}',
        display_name=f'View role for task {task.id}',
        description='View tasklog object with following joblog and logstorage',
        type=RoleTypes.hidden,
        module_name='rbac.roles',
        class_name='TaskRole',
        init_params={
            'task_id': task.id,
        },
        parametrized_by_type=[task.task_object.prototype.type],
    )
    for obj, ct in obj_type_map.items():
        for policy in Policy.objects.filter(object__object_id=obj.id, object__content_type=ct):
            for user in policy.user.all():
                try:
                    uop = UserObjectPermission.objects.get(
                        user=user, permission__codename='view_action', object_pk=task.action.pk
                    )
                except UserObjectPermission.DoesNotExist:
                    continue
                if uop in policy.user_object_perm.all() and user.has_perm(
                    f'view_{object_model}', action_object
                ):
                    policy.role.child.add(task_role)
                    apply_jobs(task, policy, user, None)
            for group in policy.group.all():
                try:
                    gop = GroupObjectPermission.objects.get(
                        group=group, permission__codename='view_action', object_pk=task.action.pk
                    )
                except UserObjectPermission.DoesNotExist:
                    continue
                if gop in policy.group_object_perm.all() and group.has_perm(
                    f'view_{object_model}', action_object
                ):
                    policy.role.child.add(task_role)
                    apply_jobs(task, policy, None, group)


class ParentRole(AbstractRole):
    """This Role is used for complex Roles that can include other Roles"""

    def find_and_apply(self, obj, policy, role, user, group=None):
        """Find Role of appropriate type and apply it to specified object"""
        for r in role.child.all():
            if r.class_name not in ('ObjectRole', 'ActionRole', 'TaskRole'):
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
