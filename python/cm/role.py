# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.  You may obtain a
# copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ruyaml

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission

import cm.checker
from cm import config
from cm.logger import log
from cm.errors import raise_AdcmEx as err
from cm.models import Role, RoleMigration


def upgrade(data):
    new_roles = {}
    for role in data['roles']:
        new_roles[role['name']] = upgrade_role(role, data)

    log.debug('NEW Roles: %s', new_roles)
    for role in data['roles']:
        role_obj = new_roles[role['name']]
        role_obj.childs.clear()
        if 'childs' not in role:
            continue
        for child in role['childs']:
            child_role = new_roles[child]
            role_obj.childs.add(child_role)
        role_obj.save()


def find_role(name, roles):
    for role in roles:
        if role['name'] == name:
            return role
    return err('INVALID_ROLE_SPEC', f'child role "{name}" is absent')


def check_roles_childs(data):
    for role in data['roles']:
        if 'childs' in role:
            for child in role['childs']:
                find_role(child, data['roles'])


def get_role_permissions(role, data):
    all_perm = []
    if 'apps' not in role:
        return []
    for app in role['apps']:
        for model in app['models']:
            try:
                ct = ContentType.objects.get(app_label=app['label'], model=model['name'])
            except ContentType.DoesNotExist:
                msg = 'no model "{}" in application "{}"'
                err('INVALID_ROLE_SPEC', msg.format(model['name'], app['label']))
            for code in model['codenames']:
                codename = f"{code}_{model['name']}"
                try:
                    perm = Permission.objects.get(content_type=ct, codename=codename)
                except Permission.DoesNotExist:
                    err('INVALID_ROLE_SPEC', f'permission with codename "{codename}" is not found')
                if perm not in all_perm:
                    all_perm.append(perm)
    return all_perm


def upgrade_role(role, data):
    perm_list = get_role_permissions(role, data['roles'])
    try:
        new_role = Role.objects.get(name=role['name'])
        new_role.permissions.clear()
    except Role.DoesNotExist:
        new_role = Role(name=role['name'])
    if 'description' in role:
        new_role.description = role['description']
    new_role.save()
    for perm in perm_list:
        new_role.permissions.add(perm)
    new_role.save()
    return new_role


def get_role_spec():
    try:
        with open(config.ROLE_SPEC, encoding='utf_8') as fd:
            data = ruyaml.round_trip_load(fd)
    except FileNotFoundError:
        err('INVALID_ROLE_SPEC', f'Can not open role file "{config.ROLE_SPEC}"')
    except (ruyaml.parser.ParserError, ruyaml.scanner.ScannerError, NotImplementedError) as e:
        err('INVALID_ROLE_SPEC', f'YAML decode "{config.ROLE_SPEC}" error: {e}')

    with open(config.ROLE_SCHEMA, encoding='utf_8') as fd:
        rules = ruyaml.round_trip_load(fd)

    try:
        cm.checker.check(data, rules)
    except cm.checker.FormatError as e:
        args = ''
        if e.errors:
            for ee in e.errors:
                if 'Input data for' in ee.message:
                    continue
                args += f'line {ee.line}: {ee}\n'
        err('INVALID_ROLE_SPEC', f'"{config.ROLE_SPEC}" line {e.line} error: {e}', args)

    return data


def init_roles():
    role_data = get_role_spec()
    check_roles_childs(role_data)

    rm = RoleMigration.obj.last()
    if rm is None:
        rm = RoleMigration(version=0)
    if role_data['version'] > rm.version:
        upgrade(role_data)
        # To do: upgrade Role's users and groups !!!
        rm.version = role_data['version']
        rm.save()
        return f'Roles are upgraded to version {rm.version}'
    else:
        return f'Roles are already at version {rm.version}'
