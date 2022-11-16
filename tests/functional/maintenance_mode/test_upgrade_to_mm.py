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

"""Test upgrade to bundle with MM directives"""

from typing import Set

import allure
import pytest
from tests.conftest import DUMMY_ACTION
from tests.functional.maintenance_mode.conftest import (
    MM_IS_OFF,
    MM_NOT_ALLOWED,
    add_hosts_to_cluster,
    check_mm_availability,
    check_mm_is,
    get_disabled_actions_names,
    get_enabled_actions_names,
    turn_mm_on,
)
from tests.functional.tools import get_object_represent
from tests.library.assertions import sets_are_equal

DUMMY_ACTION_DEFINITION = DUMMY_ACTION['dummy_action']

ALLOWED_ACTION = {'allowed_action': {**DUMMY_ACTION_DEFINITION, 'allow_in_maintenance_mode': True}}
TWO_DUMMY_ACTIONS = {'first_action': {**DUMMY_ACTION_DEFINITION}, 'second_action': {**DUMMY_ACTION_DEFINITION}}
DUMMY_ACTIONS_WITH_ALLOWED = {**TWO_DUMMY_ACTIONS, **ALLOWED_ACTION}

UPGRADE = {
    'upgrade': [
        {
            'name': 'An ice upgrade',
            'versions': {'min': 0.2, 'max': 2},
            'states': {'available': 'any', 'on_success': 'cool'},
        }
    ]
}

OLD_BUNDLE = [
    {'type': 'cluster', 'name': 'just_cluster', 'version': 1, 'actions': {**TWO_DUMMY_ACTIONS}},
    {
        'type': 'service',
        'name': 'just_service',
        'version': 1.1,
        'actions': {**TWO_DUMMY_ACTIONS},
        'components': {'just_component': {'actions': {**TWO_DUMMY_ACTIONS}}},
    },
]

NEW_BUNDLE = [{**OLD_BUNDLE[0], 'version': 2, **UPGRADE}, {**OLD_BUNDLE[1], 'version': 1.2}]


@pytest.mark.parametrize(
    'create_bundle_archives',
    [
        [
            OLD_BUNDLE,
            [
                {
                    **NEW_BUNDLE[0],
                    'allow_maintenance_mode': True,
                    'actions': {**DUMMY_ACTIONS_WITH_ALLOWED},
                },
                {
                    **NEW_BUNDLE[1],
                    'actions': {**DUMMY_ACTIONS_WITH_ALLOWED},
                    'components': {'just_component': {'actions': {**DUMMY_ACTIONS_WITH_ALLOWED}}},
                },
            ],
        ]
    ],
    indirect=True,
)
def test_allow_mm_after_upgrade(api_client, sdk_client_fs, create_bundle_archives, hosts):
    """
    Test that after upgrade to the bundle version where MM is allowed:
    - hosts in cluster set to correct MM mode
    - actions are disabled/enabled correctly
    """
    hosts_in_cluster = hosts[:3]
    free_hosts = hosts[3:]
    old_bundle, *_ = [sdk_client_fs.upload_from_fs(bundle) for bundle in create_bundle_archives]
    old_cluster = old_bundle.cluster_create('Cluster to Upgrade')
    service = old_cluster.service_add(name='just_service')
    component = service.component()

    add_hosts_to_cluster(old_cluster, hosts_in_cluster)
    old_cluster.hostcomponent_set(*[(host, component) for host in hosts_in_cluster])
    check_mm_availability(MM_NOT_ALLOWED, *hosts)

    upgrade_task = old_cluster.upgrade().do()
    if upgrade_task:
        upgrade_task.wait()

    check_mm_is(MM_IS_OFF, *hosts_in_cluster)
    check_mm_availability(MM_NOT_ALLOWED, *free_hosts)

    check_actions_are_disabled_correctly(set(DUMMY_ACTIONS_WITH_ALLOWED.keys()), set(), old_cluster, service, component)
    turn_mm_on(api_client, hosts_in_cluster[0])
    check_actions_are_disabled_correctly(
        set(ALLOWED_ACTION.keys()), set(TWO_DUMMY_ACTIONS.keys()), old_cluster, service, component
    )


@pytest.mark.parametrize(
    'create_bundle_archives',
    [[OLD_BUNDLE, [{**NEW_BUNDLE[0], 'allow_maintenance_mode': False}, {**NEW_BUNDLE[1]}]]],
    indirect=True,
)
def test_upgrade_to_mm_false(sdk_client_fs, create_bundle_archives, hosts):
    """
    Test upgrade from version without `allow_maintenance_mode` to `allow_maintenance_mode: false`
    """
    old_bundle, *_ = [sdk_client_fs.upload_from_fs(bundle) for bundle in create_bundle_archives]
    old_cluster = old_bundle.cluster_create('Cluster to Upgrade')
    service = old_cluster.service_add(name='just_service')
    component = service.component()
    cluster_hosts = [old_cluster.host_add(host) for host in hosts]
    old_cluster.hostcomponent_set(*[(h, component) for h in cluster_hosts])

    check_mm_availability(MM_NOT_ALLOWED, *cluster_hosts)

    upgrade_task = old_cluster.upgrade().do()
    if upgrade_task:
        upgrade_task.wait()

    check_mm_availability(MM_NOT_ALLOWED, *cluster_hosts)
    check_actions_are_disabled_correctly(set(TWO_DUMMY_ACTIONS.keys()), set(), old_cluster, service, component)


@pytest.mark.parametrize(
    'create_bundle_archives',
    [
        [
            [{**OLD_BUNDLE[0], 'allow_maintenance_mode': True}, {**OLD_BUNDLE[1]}],
            [{**NEW_BUNDLE[0], 'allow_maintenance_mode': False}, {**NEW_BUNDLE[1]}],
        ]
    ],
    indirect=True,
)
def test_upgrade_from_true_to_false_mm(api_client, sdk_client_fs, create_bundle_archives, hosts):
    """
    Test upgrade from version with `allow_maintenance_mode: true` to `allow_maintenance_mode: false`
    """
    old_bundle, *_ = [sdk_client_fs.upload_from_fs(bundle) for bundle in create_bundle_archives]
    old_cluster = old_bundle.cluster_create('Cluster to Upgrade')
    cluster_hosts = [old_cluster.host_add(host) for host in hosts]
    service = old_cluster.service_add(name='just_service')
    component = service.component()
    old_cluster.hostcomponent_set(*[(h, component) for h in cluster_hosts])

    check_mm_is(MM_IS_OFF, *cluster_hosts)
    turn_mm_on(api_client, cluster_hosts[0])

    upgrade_task = old_cluster.upgrade().do()
    if upgrade_task:
        upgrade_task.wait()

    check_mm_availability(MM_NOT_ALLOWED, *cluster_hosts)
    check_actions_are_disabled_correctly(set(TWO_DUMMY_ACTIONS.keys()), set(), old_cluster, service, component)


@pytest.mark.parametrize(
    'create_bundle_archives',
    [
        [
            [
                {
                    **OLD_BUNDLE[0],
                    'allow_maintenance_mode': True,
                    'actions': {
                        'disabled_at_first': {**DUMMY_ACTION_DEFINITION, 'allow_in_maintenance_mode': False},
                        'enabled_at_first': {**DUMMY_ACTION_DEFINITION, 'allow_in_maintenance_mode': True},
                    },
                },
                {**OLD_BUNDLE[1]},
            ],
            [
                {
                    **NEW_BUNDLE[0],
                    'allow_maintenance_mode': True,
                    'actions': {
                        'disabled_at_first': {**DUMMY_ACTION_DEFINITION, 'allow_in_maintenance_mode': True},
                        'enabled_at_first': {**DUMMY_ACTION_DEFINITION, 'allow_in_maintenance_mode': False},
                    },
                },
                {**NEW_BUNDLE[1]},
            ],
        ]
    ],
    indirect=True,
)
def test_allowed_actions_changed(api_client, sdk_client_fs, create_bundle_archives, hosts):
    """
    Test upgrade when allowed/disallowed in MM actions changed
    """
    old_bundle, *_ = [sdk_client_fs.upload_from_fs(bundle) for bundle in create_bundle_archives]
    old_cluster = old_bundle.cluster_create('Cluster with allowed actions changed')

    add_hosts_to_cluster(old_cluster, hosts)
    old_cluster.hostcomponent_set((hosts[0], old_cluster.service_add(name='just_service').component()))
    turn_mm_on(api_client, hosts[0])

    check_actions_are_disabled_correctly({'enabled_at_first'}, {'disabled_at_first'}, old_cluster)

    task = old_cluster.upgrade().do()
    if task:
        task.wait()

    check_actions_are_disabled_correctly({'disabled_at_first'}, {'enabled_at_first'}, old_cluster)


@allure.step('Check correct actions are enabled/disabled due to host in MM')
def check_actions_are_disabled_correctly(enabled_actions: Set[str], disabled_actions: Set[str], *objects):
    """Check that actions are disabled correctly based on their names"""
    for adcm_object in objects:
        object_represent = get_object_represent(adcm_object)
        enabled = get_enabled_actions_names(adcm_object)
        sets_are_equal(enabled, enabled_actions, f'Not all actions are enabled on {object_represent}')
        disabled = get_disabled_actions_names(adcm_object)
        sets_are_equal(disabled, disabled_actions, f'Not all actions are disabled on {object_represent}')
