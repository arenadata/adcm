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

"""Init or upgrade RBAC roles and permissions"""

import cm.checker
import ruyaml
from cm.errors import raise_adcm_ex
from cm.models import Action, Bundle, Host, ProductCategory, get_model_by_type
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from rbac import log
from rbac.models import Permission, Role, RoleMigration, RoleTypes, re_apply_all_polices
from rbac.settings import api_settings


def upgrade(data: dict):
    """Upgrade roles and user permissions"""
    new_roles = {}
    for role in data["roles"]:
        new_roles[role["name"]] = upgrade_role(role, data)

    for role in data["roles"]:
        role_obj = new_roles[role["name"]]
        task_roles = []
        for child in role_obj.child.all():
            if child.class_name == "TaskRole":
                task_roles.append(child)
        role_obj.child.clear()
        if "child" not in role:
            continue
        for child in role["child"]:
            child_role = new_roles[child]
            role_obj.child.add(child_role)
        role_obj.child.add(*task_roles)
        role_obj.save()


def find_role(name: str, roles: list):
    """search role in role list by name"""
    for role in roles:
        if role["name"] == name:
            return role
    return raise_adcm_ex("INVALID_ROLE_SPEC", f'child role "{name}" is absent')


def check_roles_child(data: dict):
    """Check if role child name are exist in specification file"""
    for role in data["roles"]:
        if "child" in role:
            for child in role["child"]:
                find_role(child, data["roles"])


def get_role_permissions(role: dict, data: dict) -> list[Permission]:  # pylint: disable=unused-argument
    """Retrieve all role's permissions"""

    all_perm = []
    if "apps" not in role:
        return []

    for app in role["apps"]:
        for model in app["models"]:
            content_type = None
            try:
                content_type = ContentType.objects.get(app_label=app["label"], model=model["name"])
            except ContentType.DoesNotExist:
                msg = 'no model "{}" in application "{}"'
                raise_adcm_ex("INVALID_ROLE_SPEC", msg.format(model["name"], app["label"]))

            for code in model["codenames"]:
                codename = f"{code}_{model['name']}"
                try:
                    perm = Permission.objects.get(content_type=content_type, codename=codename)
                except Permission.DoesNotExist:
                    perm = Permission(content_type=content_type, codename=codename)
                    perm.save()

                if perm not in all_perm:
                    all_perm.append(perm)

    return all_perm


def upgrade_role(role: dict, data: dict) -> Role:
    """Upgrade single role"""
    perm_list = get_role_permissions(role, data["roles"])
    try:
        new_role = Role.objects.get(name=role["name"], built_in=True)
        new_role.permissions.clear()
    except Role.DoesNotExist:
        new_role = Role(name=role["name"])
        new_role.save()
    new_role.module_name = role["module_name"]
    new_role.class_name = role["class_name"]
    if "init_params" in role:
        new_role.init_params = role["init_params"]
    if "description" in role:
        new_role.description = role["description"]
    if "display_name" in role:
        new_role.display_name = role["display_name"]
    else:
        new_role.display_name = role["name"]
    if "parametrized_by" in role:
        new_role.parametrized_by_type = role["parametrized_by"]
    if "type" in role:
        new_role.type = role["type"]
    for perm in perm_list:
        new_role.permissions.add(perm)
    for category_value in role.get("category", []):
        category = ProductCategory.objects.get(value=category_value)
        new_role.category.add(category)
    new_role.any_category = role.get("any_category", False)
    new_role.save()
    return new_role


def get_role_spec(data: str, schema: str) -> dict:
    """
    Read and parse roles specification from role_spec.yaml file.
    Specification file structure is checked against role_schema.yaml file.
    (see https://github.com/arenadata/yspec for details about schema syntaxis)
    """

    try:
        with open(data, encoding=settings.ENCODING_UTF_8) as f:
            data = ruyaml.round_trip_load(f)
    except FileNotFoundError:
        raise_adcm_ex("INVALID_ROLE_SPEC", f'Can not open role file "{data}"')
    except (ruyaml.parser.ParserError, ruyaml.scanner.ScannerError, NotImplementedError) as e:
        raise_adcm_ex("INVALID_ROLE_SPEC", f'YAML decode "{data}" error: {e}')

    with open(schema, encoding=settings.ENCODING_UTF_8) as f:
        rules = ruyaml.round_trip_load(f)

    try:
        cm.checker.check(data, rules)
    except cm.checker.FormatError as e:
        args = ""
        if e.errors:
            for error in e.errors:
                if "Input data for" in error.message:
                    continue

                args += f"line {error.line}: {error}\n"

        raise_adcm_ex("INVALID_ROLE_SPEC", f"line {e.line} error: {e}", args)

    return data


def get_perm(content_type, codename, name=None):
    if name:
        perm, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            name=name,
        )
    else:
        perm, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
        )

    return perm


def prepare_hidden_roles(bundle: Bundle):
    """Prepares hidden roles"""

    hidden_roles = {}
    for act in Action.objects.filter(prototype__bundle=bundle):
        name_prefix = f"{act.prototype.type} action:".title()
        name = f"{name_prefix} {act.display_name}"
        model = get_model_by_type(act.prototype.type)
        if act.prototype.type == "component":
            serv_name = f"service_{act.prototype.parent.name}_"
        else:
            serv_name = ""

        role_name = (
            f"{bundle.name}_{bundle.version}_{bundle.edition}_{serv_name}"
            f"{act.prototype.type}_{act.prototype.display_name}_{act.name}"
        )
        role, _ = Role.objects.get_or_create(
            name=role_name,
            display_name=role_name,
            description=f"run action {act.name} of {act.prototype.type} {act.prototype.display_name}",
            bundle=bundle,
            type=RoleTypes.HIDDEN,
            module_name="rbac.roles",
            class_name="ActionRole",
            init_params={
                "action_id": act.id,
                "app_name": "cm",
                "model": model.__name__,
                "filter": {
                    "prototype__name": act.prototype.name,
                    "prototype__type": act.prototype.type,
                    "prototype__bundle_id": bundle.id,
                },
            },
            parametrized_by_type=[act.prototype.type],
        )
        role.save()
        if bundle.category:
            role.category.add(bundle.category)

        content_type = ContentType.objects.get_for_model(model)
        model_name = model.__name__.lower()
        role.permissions.add(get_perm(content_type, f"view_{model_name}"))
        if name not in hidden_roles:
            hidden_roles[name] = {"parametrized_by_type": act.prototype.type, "children": []}

        hidden_roles[name]["children"].append(role)
        if act.host_action:
            ct_host = ContentType.objects.get_for_model(Host)
            role.permissions.add(get_perm(ct_host, "view_host"))
            role.permissions.add(
                get_perm(ct_host, f"run_action_{act.display_name}", f"Can run {act.display_name} actions"),
            )
        else:
            role.permissions.add(
                get_perm(content_type, f"run_action_{act.display_name}", f"Can run {act.display_name} actions"),
            )

    return hidden_roles


def update_built_in_roles(bundle: Bundle, business_role: Role, parametrized_by_type: list, built_in_roles: dict):
    """Add action role to built-in roles"""
    if "cluster" in parametrized_by_type:
        if bundle.category:
            business_role.category.add(bundle.category)
        built_in_roles["Cluster Administrator"].child.add(business_role)
    elif "service" in parametrized_by_type or "component" in parametrized_by_type:
        if bundle.category:
            business_role.category.add(bundle.category)
        built_in_roles["Cluster Administrator"].child.add(business_role)
        built_in_roles["Service Administrator"].child.add(business_role)
    elif "provider" in parametrized_by_type:
        built_in_roles["Provider Administrator"].child.add(business_role)
    elif "host" in parametrized_by_type:
        built_in_roles["Cluster Administrator"].child.add(business_role)
        built_in_roles["Provider Administrator"].child.add(business_role)


@transaction.atomic
def prepare_action_roles(bundle: Bundle):
    """Prepares action roles"""

    built_in_roles = {
        "Cluster Administrator": Role.objects.get(name="Cluster Administrator"),
        "Provider Administrator": Role.objects.get(name="Provider Administrator"),
        "Service Administrator": Role.objects.get(name="Service Administrator"),
    }
    hidden_roles = prepare_hidden_roles(bundle)
    for business_role_name, business_role_params in hidden_roles.items():
        if business_role_params["parametrized_by_type"] == "component":
            parametrized_by_type = ["service", "component"]
        else:
            parametrized_by_type = [business_role_params["parametrized_by_type"]]

        business_role, is_created = Role.objects.get_or_create(
            name=f"{business_role_name}",
            display_name=f"{business_role_name}",
            description=f"{business_role_name}",
            type=RoleTypes.BUSINESS,
            module_name="rbac.roles",
            class_name="ParentRole",
            parametrized_by_type=parametrized_by_type,
        )

        if is_created:
            log.info('Create business permission "%s"', business_role_name)

        business_role.child.add(*business_role_params["children"])
        update_built_in_roles(bundle, business_role, parametrized_by_type, built_in_roles)


def update_all_bundle_roles():
    for bundle in Bundle.objects.exclude(name="ADCM"):
        prepare_action_roles(bundle)
        msg = f'Prepare roles for "{bundle.name}" bundle.'
        log.info(msg)


def init_roles():
    """
    Init or upgrade roles and permissions in DB
    To run upgrade call
    manage.py upgraderole
    """

    role_data = get_role_spec(api_settings.ROLE_SPEC, api_settings.ROLE_SCHEMA)
    check_roles_child(role_data)

    role_migration = RoleMigration.objects.last()
    if role_migration is None:
        role_migration = RoleMigration(version=0)

    if role_data["version"] > role_migration.version:
        with transaction.atomic():
            upgrade(role_data)
            role_migration.version = role_data["version"]
            role_migration.save()
            update_all_bundle_roles()
            re_apply_all_polices()
            msg = f"Roles are upgraded to version {role_migration.version}"
            log.info(msg)
    else:
        msg = f"Roles are already at version {role_migration.version}"

    return msg
