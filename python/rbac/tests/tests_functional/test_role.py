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
import json

import pytest
from cm.models import (
    Action,
    ActionType,
    Bundle,
    Cluster,
    ClusterObject,
    ProductCategory,
    Prototype,
    ServiceComponent,
)
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from init_db import init as init_adcm
from rbac.models import Role, RoleTypes
from rbac.upgrade.role import init_roles, prepare_action_roles


@pytest.fixture()
def sample_bundle():
    init_adcm()
    init_roles()

    category = ProductCategory.objects.create(
        value='Sample Cluster',
        visible=True,
    )
    bundle = Bundle.objects.create(
        name='sample_bundle',
        version='1.0',
        hash='47b820a6d66a90b02b42017269904ab2c954bceb',
        edition='community',
        license='absent',
        category=category,
    )

    cluster_prototype = Prototype.objects.create(
        bundle=bundle,
        type='cluster',
        name='sample_cluster',
        version='1.0',
        display_name='Sample Cluster',
    )
    service_1_prototype = Prototype.objects.create(
        bundle=bundle,
        type='service',
        name='service_1',
        version='1.0',
        display_name='Service 1',
    )

    service_2_prototype = Prototype.objects.create(
        bundle=bundle,
        type='service',
        name='service_2',
        version='1.0',
        display_name='Service 2',
    )

    component_1_1_prototype = Prototype.objects.create(
        bundle=bundle,
        type='component',
        name='component_1',
        version='1.0',
        display_name='Component 1 from Service 1',
        parent=service_1_prototype,
    )
    component_2_1_prototype = Prototype.objects.create(
        bundle=bundle,
        type='component',
        name='component_2',
        version='1.0',
        display_name='Component 2 from Service 1',
        parent=service_1_prototype,
    )
    component_1_2_prototype = Prototype.objects.create(
        bundle=bundle,
        type='component',
        name='component_1',
        version='1.0',
        display_name='Component 1 from Service 2',
        parent=service_2_prototype,
    )
    component_2_2_prototype = Prototype.objects.create(
        bundle=bundle,
        type='component',
        name='component_2',
        version='1.0',
        display_name='Component 2 from Service 2',
        parent=service_2_prototype,
    )
    actions = [
        Action(
            name='cluster_action',
            type=ActionType.Job,
            script='./action.yaml',
            script_type='ansible',
            state_available='any',
            prototype=cluster_prototype,
            display_name='Cluster Action',
        ),
        Action(
            name='service_1_action',
            type=ActionType.Job,
            script='./action.yaml',
            script_type='ansible',
            state_available='any',
            prototype=service_1_prototype,
            display_name='Service 1 Action',
        ),
        Action(
            name='component_1_1_action',
            type=ActionType.Job,
            script='./action.yaml',
            script_type='ansible',
            state_available='any',
            prototype=component_1_1_prototype,
            display_name='Component 1 from Service 1 Action',
        ),
        Action(
            name='component_2_1_action',
            type=ActionType.Job,
            script='./action.yaml',
            script_type='ansible',
            state_available='any',
            prototype=component_2_1_prototype,
            display_name='Component 2 from Service 1 Action',
        ),
        Action(
            name='service_2_action',
            type=ActionType.Job,
            script='./action.yaml',
            script_type='ansible',
            state_available='any',
            prototype=service_2_prototype,
            display_name='Service 2 Action',
        ),
        Action(
            name='component_1_2_action',
            type=ActionType.Job,
            script='./action.yaml',
            script_type='ansible',
            state_available='any',
            prototype=component_1_2_prototype,
            display_name='Component 1 from Service 2 Action',
        ),
        Action(
            name='component_2_2_action',
            type=ActionType.Job,
            script='./action.yaml',
            script_type='ansible',
            state_available='any',
            prototype=component_2_2_prototype,
            display_name='Component 2 from Service 2 Action',
        ),
    ]
    Action.objects.bulk_create(actions)
    return bundle


def check_roles(bundle):
    roles = [
        # hidden action roles
        {
            'name': 'sample_bundle_1.0_community_cluster_Sample Cluster_cluster_action',
            'display_name': 'sample_bundle_1.0_community_cluster_Sample Cluster_cluster_action',
            'bundle': bundle,
            'type': RoleTypes.hidden,
            'module_name': 'rbac.roles',
            'class_name': 'ActionRole',
            'init_params': {
                'action_id': 3,
                'app_name': 'cm',
                'model': 'Cluster',
                'filter': {
                    'prototype__name': 'sample_cluster',
                    'prototype__type': 'cluster',
                    'prototype__bundle_id': bundle.id,
                },
            },
            'parametrized_by_type': ['cluster'],
        },
        {
            'name': 'sample_bundle_1.0_community_service_Service 1_service_1_action',
            'display_name': 'sample_bundle_1.0_community_service_Service 1_service_1_action',
            'bundle': bundle,
            'type': RoleTypes.hidden,
            'module_name': 'rbac.roles',
            'class_name': 'ActionRole',
            'init_params': {
                'action_id': 4,
                'app_name': 'cm',
                'model': 'ClusterObject',
                'filter': {
                    'prototype__name': 'service_1',
                    'prototype__type': 'service',
                    'prototype__bundle_id': bundle.id,
                },
            },
            'parametrized_by_type': ['service'],
        },
        {
            'name': (
                'sample_bundle_1.0_community_service_service_1_'
                'component_Component 1 from Service 1_component_1_1_action'
            ),
            'display_name': (
                'sample_bundle_1.0_community_service_service_1_'
                'component_Component 1 from Service 1_component_1_1_action'
            ),
            'bundle': bundle,
            'type': RoleTypes.hidden,
            'module_name': 'rbac.roles',
            'class_name': 'ActionRole',
            'init_params': {
                'action_id': 5,
                'app_name': 'cm',
                'model': 'ServiceComponent',
                'filter': {
                    'prototype__name': 'component_1',
                    'prototype__type': 'component',
                    'prototype__bundle_id': bundle.id,
                },
            },
            'parametrized_by_type': ['component'],
        },
        {
            'name': (
                'sample_bundle_1.0_community_service_service_1_'
                'component_Component 2 from Service 1_component_2_1_action'
            ),
            'display_name': (
                'sample_bundle_1.0_community_service_service_1_'
                'component_Component 2 from Service 1_component_2_1_action'
            ),
            'bundle': bundle,
            'type': RoleTypes.hidden,
            'module_name': 'rbac.roles',
            'class_name': 'ActionRole',
            'init_params': {
                'action_id': 6,
                'app_name': 'cm',
                'model': 'ServiceComponent',
                'filter': {
                    'prototype__name': 'component_2',
                    'prototype__type': 'component',
                    'prototype__bundle_id': bundle.id,
                },
            },
            'parametrized_by_type': ['component'],
        },
        {
            'name': 'sample_bundle_1.0_community_service_Service 2_service_2_action',
            'display_name': 'sample_bundle_1.0_community_service_Service 2_service_2_action',
            'bundle': bundle,
            'type': RoleTypes.hidden,
            'module_name': 'rbac.roles',
            'class_name': 'ActionRole',
            'init_params': {
                'action_id': 7,
                'app_name': 'cm',
                'model': 'ClusterObject',
                'filter': {
                    'prototype__name': 'service_2',
                    'prototype__type': 'service',
                    'prototype__bundle_id': bundle.id,
                },
            },
            'parametrized_by_type': ['service'],
        },
        {
            'name': (
                'sample_bundle_1.0_community_service_service_2_'
                'component_Component 1 from Service 2_component_1_2_action'
            ),
            'display_name': (
                'sample_bundle_1.0_community_service_service_2_'
                'component_Component 1 from Service 2_component_1_2_action'
            ),
            'bundle': bundle,
            'type': RoleTypes.hidden,
            'module_name': 'rbac.roles',
            'class_name': 'ActionRole',
            'init_params': {
                'action_id': 8,
                'app_name': 'cm',
                'model': 'ServiceComponent',
                'filter': {
                    'prototype__name': 'component_1',
                    'prototype__type': 'component',
                    'prototype__bundle_id': bundle.id,
                },
            },
            'parametrized_by_type': ['component'],
        },
        {
            'name': (
                'sample_bundle_1.0_community_service_service_2_'
                'component_Component 2 from Service 2_component_2_2_action'
            ),
            'display_name': (
                'sample_bundle_1.0_community_service_service_2_'
                'component_Component 2 from Service 2_component_2_2_action'
            ),
            'bundle': bundle,
            'type': RoleTypes.hidden,
            'module_name': 'rbac.roles',
            'class_name': 'ActionRole',
            'init_params': {
                'action_id': 9,
                'app_name': 'cm',
                'model': 'ServiceComponent',
                'filter': {
                    'prototype__name': 'component_2',
                    'prototype__type': 'component',
                    'prototype__bundle_id': bundle.id,
                },
            },
            'parametrized_by_type': ['component'],
        },
        # business action roles
        {
            'name': 'Cluster Action: Cluster Action',
            'display_name': 'Cluster Action: Cluster Action',
            'description': 'Cluster Action: Cluster Action',
            'type': RoleTypes.business,
            'module_name': 'rbac.roles',
            'class_name': 'ParentRole',
            'parametrized_by_type': ['cluster'],
        },
        {
            'name': 'Service Action: Service 1 Action',
            'display_name': 'Service Action: Service 1 Action',
            'description': 'Service Action: Service 1 Action',
            'type': RoleTypes.business,
            'module_name': 'rbac.roles',
            'class_name': 'ParentRole',
            'parametrized_by_type': ['service'],
        },
        {
            'name': 'Component Action: Component 1 from Service 1 Action',
            'display_name': 'Component Action: Component 1 from Service 1 Action',
            'description': 'Component Action: Component 1 from Service 1 Action',
            'type': RoleTypes.business,
            'module_name': 'rbac.roles',
            'class_name': 'ParentRole',
            'parametrized_by_type': ['service', 'component'],
        },
        {
            'name': 'Component Action: Component 2 from Service 1 Action',
            'display_name': 'Component Action: Component 2 from Service 1 Action',
            'description': 'Component Action: Component 2 from Service 1 Action',
            'type': RoleTypes.business,
            'module_name': 'rbac.roles',
            'class_name': 'ParentRole',
            'parametrized_by_type': ['service', 'component'],
        },
        {
            'name': 'Service Action: Service 2 Action',
            'display_name': 'Service Action: Service 2 Action',
            'description': 'Service Action: Service 2 Action',
            'type': RoleTypes.business,
            'module_name': 'rbac.roles',
            'class_name': 'ParentRole',
            'parametrized_by_type': ['service'],
        },
        {
            'name': 'Component Action: Component 1 from Service 2 Action',
            'display_name': 'Component Action: Component 1 from Service 2 Action',
            'description': 'Component Action: Component 1 from Service 2 Action',
            'type': RoleTypes.business,
            'module_name': 'rbac.roles',
            'class_name': 'ParentRole',
            'parametrized_by_type': ['service', 'component'],
        },
        {
            'name': 'Component Action: Component 2 from Service 2 Action',
            'display_name': 'Component Action: Component 2 from Service 2 Action',
            'description': 'Component Action: Component 2 from Service 2 Action',
            'type': RoleTypes.business,
            'module_name': 'rbac.roles',
            'class_name': 'ParentRole',
            'parametrized_by_type': ['service', 'component'],
        },
    ]
    for role_data in roles:
        count = Role.objects.filter(**role_data).count()
        assert count == 1, (
            f'Role does not exist or not unique: {count} > 1\n'
            f'{json.dumps(role_data, indent=2, default=str)}'
        )
        role = Role.objects.filter(**role_data).first()
        if role == RoleTypes.business:
            assert role.child.count() == 1, 'Role cannot have more than one child.'
        if role == RoleTypes.hidden:
            assert not role.child.exists(), 'Role cannot have children.'

    ca_role = Role.objects.get(name='Cluster Administrator')
    assert (
        ca_role.child.filter(name='Cluster Action: Cluster Action').count() == 1
    ), 'Cluster Action: Cluster Action role missing from base role'
    sa_role = Role.objects.get(name='Service Administrator')
    assert (
        sa_role.child.filter(
            name__in=[
                'Service Action: Service 1 Action',
                'Component Action: Component 1 from Service 1 Action',
                'Component Action: Component 2 from Service 1 Action',
                'Service Action: Service 2 Action',
                'Component Action: Component 1 from Service 2 Action',
                'Component Action: Component 2 from Service 2 Action',
            ]
        ).count()
        == 6
    ), 'Roles missing from base roles'


def check_permission():
    permissions = [
        {
            'content_type': ContentType.objects.get_for_model(Cluster),
            'codename': 'run_action_Cluster Action',
            'name': 'Can run Cluster Action actions',
        },
        {
            'content_type': ContentType.objects.get_for_model(ClusterObject),
            'codename': 'run_action_Service 1 Action',
            'name': 'Can run Service 1 Action actions',
        },
        {
            'content_type': ContentType.objects.get_for_model(ClusterObject),
            'codename': 'run_action_Service 2 Action',
            'name': 'Can run Service 2 Action actions',
        },
        {
            'content_type': ContentType.objects.get_for_model(ServiceComponent),
            'codename': 'run_action_Component 1 from Service 1 Action',
            'name': 'Can run Component 1 from Service 1 Action actions',
        },
        {
            'content_type': ContentType.objects.get_for_model(ServiceComponent),
            'codename': 'run_action_Component 2 from Service 1 Action',
            'name': 'Can run Component 2 from Service 1 Action actions',
        },
        {
            'content_type': ContentType.objects.get_for_model(ServiceComponent),
            'codename': 'run_action_Component 1 from Service 2 Action',
            'name': 'Can run Component 1 from Service 2 Action actions',
        },
        {
            'content_type': ContentType.objects.get_for_model(ServiceComponent),
            'codename': 'run_action_Component 2 from Service 2 Action',
            'name': 'Can run Component 2 from Service 2 Action actions',
        },
    ]
    for permission_data in permissions:
        assert (
            Permission.objects.filter(**permission_data).count() == 1
        ), f'Permission does not exist:\n{json.dumps(permission_data, default=str, indent=2)}'


@pytest.mark.django_db
def test_cook_roles(sample_bundle):  # pylint: disable=redefined-outer-name
    prepare_action_roles(sample_bundle)
    check_roles(sample_bundle)
    check_permission()
