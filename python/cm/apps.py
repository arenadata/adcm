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
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import AppConfig
from django.db.models.signals import post_migrate


ops_model_list = [
    'adcm',
    'bundle',
    'prototype',
    'upgrade',
    'tasklog',
    'joblog',
    'logstorage',
    'cluster',
    'clusterbind',
    'clusterobject',
    'servicecomponent',
    'hostcomponent',
    'hostprovider',
    'host',
    'action',
    'configlog',
    'userprofile',
]

auth_model_list = ['user', 'group', 'role']


def fill_view_role(Role, Permission):
    if Role.objects.filter(name='view'):
        return
    role = Role(name='view', description='View all data')
    role.save()
    for model in ops_model_list + auth_model_list:
        codename = f'view_{model}'
        perm = Permission.objects.get(codename=codename)
        role.permissions.add(perm)
    role.save()


def fill_admin_role(Role, Permission):
    if Role.objects.filter(name='admin'):
        return
    role = Role(name='admin', description='Admin clusters')
    role.save()
    for model in auth_model_list:
        codename = f'view_{model}'
        perm = Permission.objects.get(codename=codename)
        role.permissions.add(perm)
    for model in ops_model_list:
        for mod in ('view', 'add', 'change', 'delete'):
            codename = f'{mod}_{model}'
            perm = Permission.objects.get(codename=codename)
            role.permissions.add(perm)
    role.save()


def fill_role(apps, **kwargs):
    Role = apps.get_model('cm', 'Role')
    Permission = apps.get_model('auth', 'Permission')
    fill_view_role(Role, Permission)
    fill_admin_role(Role, Permission)


class CmConfig(AppConfig):
    name = 'cm'

    def ready(self):
        post_migrate.connect(fill_role, sender=self)
