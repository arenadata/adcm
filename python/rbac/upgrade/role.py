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

from hashlib import sha256

from cm.checker import FormatError, check
from cm.errors import raise_adcm_ex
from cm.logger import logger
from cm.models import Action, Bundle, Host, ProductCategory, get_model_by_type
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from rbac.models import Permission, Policy, Role, RoleMigration, RoleTypes
from rbac.settings import api_settings
from ruyaml import round_trip_load
from ruyaml.parser import ParserError
from ruyaml.scanner import ScannerError


def upgrade(data: dict) -> None:
    new_roles = {}
    for role_data in data["roles"]:
        new_roles[role_data["name"]] = upgrade_role(role_data=role_data)

    for role_data in data["roles"]:
        role_obj = new_roles[role_data["name"]]
        task_roles = []
        for child in role_obj.child.order_by("id"):
            if child.class_name == "TaskRole":
                task_roles.append(child)

        role_obj.child.clear()
        if "child" not in role_data:
            continue

        for child in role_data["child"]:
            child_role = new_roles[child]
            role_obj.child.add(child_role)

        role_obj.child.add(*task_roles)
        role_obj.save()


def get_role_permissions(role_data: dict) -> list[Permission]:
    all_permissions = []
    if "apps" not in role_data:
        return all_permissions

    for app in role_data["apps"]:
        for model in app["models"]:
            content_type = None
            try:
                content_type = ContentType.objects.get(app_label=app["label"], model=model["name"])
            except ContentType.DoesNotExist:
                raise_adcm_ex(
                    code="INVALID_ROLE_SPEC", msg=f'no model "{model["name"]}" in application "{app["label"]}"'
                )

            for code in model["codenames"]:
                codename = f"{code}_{model['name']}"
                try:
                    permission = Permission.objects.get(content_type=content_type, codename=codename)
                except Permission.DoesNotExist:
                    permission = Permission(content_type=content_type, codename=codename)
                    permission.save()

                if permission not in all_permissions:
                    all_permissions.append(permission)

    return all_permissions


def upgrade_role(role_data: dict) -> Role:
    perm_list = get_role_permissions(role_data=role_data)
    try:
        new_role = Role.objects.get(name=role_data["name"], built_in=True)
        new_role.permissions.clear()
    except Role.DoesNotExist:
        new_role = Role(name=role_data["name"])
        new_role.save()

    new_role.module_name = role_data["module_name"]
    new_role.class_name = role_data["class_name"]
    if "init_params" in role_data:
        new_role.init_params = role_data["init_params"]

    if "description" in role_data:
        new_role.description = role_data["description"]

    if "display_name" in role_data:
        new_role.display_name = role_data["display_name"]
    else:
        new_role.display_name = role_data["name"]

    if "parametrized_by" in role_data:
        new_role.parametrized_by_type = role_data["parametrized_by"]

    if "type" in role_data:
        new_role.type = role_data["type"]

    for perm in perm_list:
        new_role.permissions.add(perm)

    for category_value in role_data.get("category", []):
        category = ProductCategory.objects.get(value=category_value)
        new_role.category.add(category)

    new_role.any_category = role_data.get("any_category", False)
    new_role.save()

    return new_role


def get_role_spec(data: str, schema: str) -> dict:
    """
    Read and parse roles specification from role_spec.yaml file.
    Specification file structure is checked against role_schema.yaml file.
    (see https://github.com/arenadata/yspec for details about schema syntax)
    """

    try:
        with open(file=data, encoding=settings.ENCODING_UTF_8) as f:
            data = round_trip_load(stream=f)
    except FileNotFoundError:
        raise_adcm_ex(code="INVALID_ROLE_SPEC", msg=f'Can not open role file "{data}"')

    except (ParserError, ScannerError, NotImplementedError) as e:
        raise_adcm_ex(code="INVALID_ROLE_SPEC", msg=f'YAML decode "{data}" error: {e}')

    with open(file=schema, encoding=settings.ENCODING_UTF_8) as f:
        rules = round_trip_load(stream=f)

    try:
        check(data=data, rules=rules)
    except FormatError as e:
        args = ""
        if e.errors:
            for error in e.errors:
                if "Input data for" in error.message:
                    continue

                args = f"{args}line {error.line}: {error}\n"

        raise_adcm_ex(code="INVALID_ROLE_SPEC", msg=f"line {e.line} error: {e}", args=args)

    return data


def prepare_hidden_roles(bundle: Bundle) -> dict:
    hidden_roles = {}

    for action in Action.objects.filter(prototype__bundle=bundle):
        name_prefix = f"{action.prototype.type} action:".title()
        name = f"{name_prefix} {action.display_name}"
        model = get_model_by_type(action.prototype.type)

        if action.prototype.type == "component":
            serv_name = f"service_{action.prototype.parent.name}_"
        else:
            serv_name = ""

        role_name = (
            f"{bundle.name}_{bundle.version}_{bundle.edition}_{serv_name}"
            f"{action.prototype.type}_{action.prototype.display_name}_{action.name}"
        )
        role, _ = Role.objects.get_or_create(
            name=role_name,
            display_name=role_name,
            description=f"run action {action.name} of {action.prototype.type} {action.prototype.display_name}",
            bundle=bundle,
            type=RoleTypes.HIDDEN,
            module_name="rbac.roles",
            class_name="ActionRole",
            init_params={
                "action_id": action.id,
                "app_name": "cm",
                "model": model.__name__,
                "filter": {
                    "prototype__name": action.prototype.name,
                    "prototype__type": action.prototype.type,
                    "prototype__bundle_id": bundle.id,
                },
            },
            parametrized_by_type=[action.prototype.type],
        )
        role.save()

        if bundle.category:
            role.category.add(bundle.category)

        content_type = ContentType.objects.get_for_model(model=model)
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename=f"view_{model.__name__.lower()}",
        )
        role.permissions.add(permission)

        if name not in hidden_roles:
            hidden_roles[name] = {"parametrized_by_type": action.prototype.type, "children": []}

        hidden_roles[name]["children"].append(role)
        action_name_hash = sha256(action.name.encode(settings.ENCODING_UTF_8)).hexdigest()

        action_permission, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename=f"run_action_{action_name_hash}",
            name=f"Can run {action_name_hash} actions",
        )
        role.permissions.add(action_permission)
        if action.host_action:
            permission, _ = Permission.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(Host),
                codename="view_host",
            )
            role.permissions.add(permission)

    return hidden_roles


def update_built_in_roles(
    bundle: Bundle, business_role: Role, parametrized_by_type: list, built_in_roles: dict
) -> None:
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
def prepare_action_roles(bundle: Bundle) -> None:
    built_in_roles = {
        "Cluster Administrator": Role.objects.get(name="Cluster Administrator"),
        "Provider Administrator": Role.objects.get(name="Provider Administrator"),
        "Service Administrator": Role.objects.get(name="Service Administrator"),
    }
    hidden_roles = prepare_hidden_roles(bundle=bundle)
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
            logger.info('Create business permission "%s"', business_role_name)

        business_role.child.add(*business_role_params["children"])
        update_built_in_roles(
            bundle=bundle,
            business_role=business_role,
            parametrized_by_type=parametrized_by_type,
            built_in_roles=built_in_roles,
        )


def init_roles() -> str:
    role_data = get_role_spec(data=api_settings.ROLE_SPEC, schema=api_settings.ROLE_SCHEMA)
    for role in role_data["roles"]:
        if "child" not in role:
            continue

        break_flag = False
        for child_name in role["child"]:
            for child_role in role_data["roles"]:
                if child_role["name"] == child_name:
                    break_flag = True

                    break

            if not break_flag:
                raise_adcm_ex("INVALID_ROLE_SPEC", f'child role "{child_name}" is absent')

    role_migration = RoleMigration.objects.last()
    if role_migration is None:
        role_migration = RoleMigration(version=0)

    if role_data["version"] > role_migration.version:
        with transaction.atomic():
            upgrade(data=role_data)
            role_migration.version = role_data["version"]
            role_migration.save()

            for bundle in Bundle.objects.exclude(name="ADCM"):
                prepare_action_roles(bundle=bundle)
                logger.info('Prepare roles for "%s" bundle.', bundle.name)

            for policy in Policy.objects.all():
                policy.apply()

            logger.info("Roles are upgraded to version %s", role_migration.version)
            msg = f"Roles are upgraded to version {role_migration.version}"
    else:
        msg = f"Roles are already at version {role_migration.version}"

    return msg
