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

from cm.errors import raise_adcm_ex
from cm.models import (
    Action,
    ActionHostGroup,
    ADCMEntity,
    Component,
    ConfigLog,
    GroupConfig,
    Host,
    HostComponent,
    JobLog,
    LogStorage,
    Service,
    TaskLog,
)
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.models import QuerySet
from django.db.transaction import atomic
from guardian.models import GroupObjectPermission

from rbac.models import (
    Permission,
    Policy,
    PolicyPermission,
    Role,
    RoleTypes,
    get_objects_for_policy,
)


class AbstractRole:
    class Meta:
        abstract = True

    def __init__(self, **kwargs):
        self.params = kwargs

    def apply(self, policy: Policy, role: Role, param_obj=None) -> None:
        """
        This method should apply Role to User and/or Group.
        Generally it means you should assign permissions from Role to User and/or Group
        and save links to these permissions in Policy model.
        If Role is parametrized_by_type than parametrized objects should be obtained from
        `Policy.object` field.
        Optional parameter param_obj can be used to specify the object in complex cases
        """

        raise NotImplementedError("You must provide apply method")


class ModelRole(AbstractRole):
    def apply(self, policy: Policy, role: Role, param_obj=None) -> None:  # noqa: ARG002
        for perm in role.get_permissions():
            for group in policy.group.all():
                group.permissions.add(perm)
                policy_permission, _ = PolicyPermission.objects.get_or_create(group=group, permission=perm)
                policy.model_perm.add(policy_permission)


def assign_group_perm(policy: Policy, permission: Permission, obj) -> None:
    row_template = (obj.pk, ContentType.objects.get_for_model(model=obj).pk, permission.pk)
    group_rows = [(*row_template, group_pk) for group_pk in policy.group.values_list("pk", flat=True)]

    if not group_rows:
        return

    cursor = connection.cursor()
    with atomic():
        if group_rows:
            query_str = (
                "INSERT INTO guardian_groupobjectpermission "
                "(object_pk, content_type_id, permission_id, group_id) VALUES"
            )
            for row in group_rows:
                query_str = f"{query_str} {row},"

            query_str = (
                f"{query_str[:-1]} ON CONFLICT (group_id, permission_id, object_pk) DO UPDATE SET "
                "object_pk=EXCLUDED.object_pk, content_type_id=EXCLUDED.content_type_id, "
                "permission_id=EXCLUDED.permission_id, group_id=EXCLUDED.group_id RETURNING id;"
            )
            cursor.execute(query_str)

            rows = [
                (policy.pk, group_object_permission_id)
                for group_object_permission_id in {item[0] for item in cursor.fetchall()}
            ]
            if rows:
                query_str = "INSERT INTO rbac_policy_group_object_perm (policy_id, groupobjectpermission_id) VALUES"
                for row in rows:
                    query_str = f"{query_str} {row},"

                query_str = f"{query_str[:-1]} ON CONFLICT DO NOTHING;"
                cursor.execute(query_str)


class ObjectRole(AbstractRole):
    def filter(self) -> QuerySet | None:
        if "model" not in self.params:
            return None

        try:
            return apps.get_model(self.params["app_name"], self.params["model"]).objects.filter(**self.params["filter"])
        except LookupError as e:
            raise_adcm_ex("ROLE_FILTER_ERROR", str(e))

        return None

    def apply(self, policy: Policy, role: Role, param_obj=None) -> None:
        for obj in policy.get_objects(param_obj):
            for perm in role.get_permissions():
                assign_group_perm(policy=policy, permission=perm, obj=obj)


class ActionRole(AbstractRole):
    def filter(self) -> QuerySet | None:
        if "model" not in self.params:
            return None
        try:
            return apps.get_model(self.params["app_name"], self.params["model"]).objects.filter(**self.params["filter"])
        except LookupError as e:
            raise_adcm_ex("ROLE_FILTER_ERROR", str(e))

        return None

    def apply(self, policy: Policy, role: Role, param_obj=None) -> None:
        action = Action.obj.get(id=self.params["action_id"])
        permission, _ = Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(model=Action),
            codename=f"view_{Action.__name__.lower()}",
        )
        assign_group_perm(
            policy=policy,
            permission=permission,
            obj=action,
        )
        for obj in policy.get_objects(param_obj):
            for perm in role.get_permissions():
                if action.host_action and perm.content_type == ContentType.objects.get_for_model(Host):
                    hosts = []
                    if obj.prototype.type == "cluster":
                        for host in Host.obj.filter(cluster=obj):
                            hosts.append(host)
                    elif obj.prototype.type == "service":
                        for hostcomponent in HostComponent.obj.filter(cluster=obj.cluster, service=obj):
                            hosts.append(hostcomponent.host)
                    elif obj.prototype.type == "component":
                        for hostcomponent in HostComponent.obj.filter(
                            cluster=obj.cluster, service=obj.service, component=obj
                        ):
                            hosts.append(hostcomponent.host)
                    elif obj.prototype.type == "provider":
                        for host in Host.obj.filter(provider=obj):
                            hosts.append(host)

                    for host in hosts:
                        assign_group_perm(policy=policy, permission=perm, obj=host)

                    continue

                assign_group_perm(policy=policy, permission=perm, obj=obj)


class TaskRole(AbstractRole):
    def apply(self, policy: Policy, role: Role, param_obj: ADCMEntity = None) -> None:
        task = TaskLog.objects.filter(id=self.params["task_id"]).first()
        if not task:
            role.delete()

            return

        for obj in policy.get_objects(param_obj):
            if obj == task.task_object:
                apply_jobs(task=task, policy=policy)

        return


def apply_jobs(task: TaskLog, policy: Policy) -> None:
    view_tasklog_permission, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(model=TaskLog),
        codename=f"view_{TaskLog.__name__.lower()}",
    )
    assign_group_perm(policy=policy, permission=view_tasklog_permission, obj=task)

    change_tasklog_permission, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(model=TaskLog),
        codename=f"change_{TaskLog.__name__.lower()}",
    )
    change_joblog_permission, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(model=JobLog),
        codename=f"change_{JobLog.__name__.lower()}",
    )
    assign_group_perm(policy=policy, permission=change_tasklog_permission, obj=task)

    view_joblog_permission, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(model=JobLog),
        codename=f"view_{JobLog.__name__.lower()}",
    )
    view_logstorage_permission, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(model=LogStorage),
        codename=f"view_{LogStorage.__name__.lower()}",
    )

    for job in JobLog.objects.filter(task=task):
        assign_group_perm(policy=policy, permission=view_joblog_permission, obj=job)
        assign_group_perm(policy=policy, permission=change_joblog_permission, obj=job)

        for log in LogStorage.objects.filter(job=job):
            assign_group_perm(policy=policy, permission=view_logstorage_permission, obj=log)


def re_apply_policy_for_jobs(action_object: ADCMEntity, task: TaskLog) -> None:
    obj_type_map = get_objects_for_policy(obj=action_object)
    object_model = action_object.__class__.__name__.lower()

    target = task.task_object
    if isinstance(target, ActionHostGroup):
        target = target.object

    task_role, _ = Role.objects.get_or_create(
        name=f"View role for task {task.id}",
        display_name=f"View role for task {task.id}",
        description="View tasklog object with following joblog and logstorage",
        type=RoleTypes.HIDDEN,
        module_name="rbac.roles",
        class_name="TaskRole",
        init_params={
            "task_id": task.id,
        },
        parametrized_by_type=[target.prototype.type],
    )

    for obj, content_type in obj_type_map.items():
        for policy in Policy.objects.filter(object__object_id=obj.id, object__content_type=content_type):
            for group in policy.group.all():
                try:
                    group_obj_perm = GroupObjectPermission.objects.get(
                        group=group,
                        permission__codename="view_action",
                        object_pk=task.action.pk,
                    )
                    model_view_gop = GroupObjectPermission.objects.get(
                        group=group,
                        permission__codename=f"view_{object_model}",
                        object_pk=action_object.pk,
                    )
                except GroupObjectPermission.DoesNotExist:
                    continue

                if group_obj_perm in policy.group_object_perm.all() and model_view_gop:
                    policy.role.child.add(task_role)
                    apply_jobs(task=task, policy=policy)


def apply_policy_for_new_config(config_object: ADCMEntity, config_log: ConfigLog) -> None:
    obj_type_map = get_objects_for_policy(obj=config_object)
    object_model = config_object.__class__.__name__.lower()
    permission, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(model=ConfigLog),
        codename=f"view_{ConfigLog.__name__.lower()}",
    )

    for obj, content_type in obj_type_map.items():
        for policy in Policy.objects.filter(object__object_id=obj.id, object__content_type=content_type):
            for group in policy.group.all():
                try:
                    group_obj_perm = GroupObjectPermission.objects.get(
                        group=group,
                        permission__codename="view_objectconfig",
                        object_pk=config_log.obj_ref_id,
                    )
                    model_view_gop = GroupObjectPermission.objects.get(
                        group=group,
                        permission__codename=f"view_{object_model}",
                        object_pk=config_object.pk,
                    )
                except GroupObjectPermission.DoesNotExist:
                    continue

                if group_obj_perm in policy.group_object_perm.all() and model_view_gop:
                    assign_group_perm(policy=policy, permission=permission, obj=config_log)


class ConfigRole(AbstractRole):
    def apply(self, policy: Policy, role: Role, param_obj=None) -> None:
        for obj in policy.get_objects(param_obj=param_obj):
            if obj.config is None:
                continue

            object_type = ContentType.objects.get_for_model(obj)
            config_groups = GroupConfig.objects.filter(object_type=object_type, object_id=obj.id)

            for perm in role.get_permissions():
                if perm.content_type.model == "objectconfig":
                    assign_group_perm(policy=policy, permission=perm, obj=obj.config)
                    for config_group in config_groups:
                        assign_group_perm(
                            policy=policy,
                            permission=perm,
                            obj=config_group.config,
                        )

                if perm.content_type.model == "configlog":
                    for config in obj.config.configlog_set.all():
                        assign_group_perm(policy=policy, permission=perm, obj=config)
                    for config_group in config_groups:
                        for config in config_group.config.configlog_set.all():
                            assign_group_perm(policy=policy, permission=perm, obj=config)

                if perm.content_type.model == "groupconfig":
                    for config_group in config_groups:
                        assign_group_perm(policy=policy, permission=perm, obj=config_group)


class ParentRole(AbstractRole):
    @staticmethod
    def find_and_apply(obj: ADCMEntity, policy: Policy, role: Role) -> None:
        for child_role in role.child.filter(class_name__in=("ObjectRole", "TaskRole", "ConfigRole")):
            if obj.prototype.type in child_role.parametrized_by_type:
                child_role.apply(policy=policy, obj=obj)

        for child_role in role.child.filter(class_name="ActionRole"):
            action = Action.obj.get(id=child_role.init_params["action_id"])
            if obj.prototype == action.prototype:
                child_role.apply(policy=policy, obj=obj)

    def apply(
        self,
        policy: Policy,
        role: Role,
        param_obj=None,
    ):
        for child_role in role.child.filter(class_name__in=("ModelRole", "ParentRole")):
            child_role.apply(policy=policy, obj=param_obj)

        parametrized_by = set()
        for child_role in role.child.all():
            parametrized_by.update(set(child_role.parametrized_by_type))

        for obj in policy.get_objects(param_obj=param_obj):
            self.find_and_apply(obj=obj, policy=policy, role=role)

            if obj.prototype.type == "cluster":
                if "service" in parametrized_by or "component" in parametrized_by:
                    for service in Service.obj.filter(cluster=obj):
                        self.find_and_apply(obj=service, policy=policy, role=role)
                        if "component" in parametrized_by:
                            for comp in Component.obj.filter(service=service):
                                self.find_and_apply(obj=comp, policy=policy, role=role)

                if "host" in parametrized_by:
                    for host in Host.obj.filter(cluster=obj):
                        self.find_and_apply(obj=host, policy=policy, role=role)
            elif obj.prototype.type == "service":
                if "component" in parametrized_by:
                    for comp in Component.obj.filter(service=obj):
                        self.find_and_apply(obj=comp, policy=policy, role=role)

                if "host" in parametrized_by:
                    for hostcomponent in HostComponent.obj.filter(cluster=obj.cluster, service=obj):
                        self.find_and_apply(obj=hostcomponent.host, policy=policy, role=role)

                assign_group_perm(
                    policy=policy,
                    permission=Permission.objects.get(codename="view_cluster"),
                    obj=obj.cluster,
                )
            elif obj.prototype.type == "component":
                if "host" in parametrized_by:
                    for hostcomponent in HostComponent.obj.filter(
                        cluster=obj.cluster,
                        service=obj.service,
                        component=obj,
                    ):
                        self.find_and_apply(obj=hostcomponent.host, policy=policy, role=role)

                assign_group_perm(
                    policy=policy,
                    permission=Permission.objects.get(codename="view_cluster"),
                    obj=obj.cluster,
                )
                assign_group_perm(
                    policy=policy,
                    permission=Permission.objects.get(codename="view_service"),
                    obj=obj.service,
                )
            elif obj.prototype.type == "provider":
                if "host" in parametrized_by:
                    for host in Host.obj.filter(provider=obj):
                        self.find_and_apply(obj=host, policy=policy, role=role)
