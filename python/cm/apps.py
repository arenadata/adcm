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

from functools import partial

from adwp_events.signals import m2m_change, model_change, model_delete
from django.apps import AppConfig
from django.db.models.signals import m2m_changed, post_delete, post_save

WATCHED_CM_MODELS = (
    'group-config',
    'group-config-hosts',
    'adcm-concerns',
    'cluster-concerns',
    'cluster-object-concerns',
    'service-component-concerns',
    'host-provider-concerns',
    'host-concerns',
)
WATCHED_RBAC_MODELS = (
    'user',
    'group',
    'policy',
    'role',
)


def filter_out_event(module, name, obj):
    # We filter the sending of events only for cm and rbac applications
    # 'AnonymousUser', 'admin', 'status' are filtered out due to adwp_event design issue
    if module in ['rbac.models'] and name in WATCHED_RBAC_MODELS:
        if name == 'user' and obj.username in ['AnonymousUser', 'admin', 'status', 'system']:
            return True
        return False
    if module in ['cm.models'] and name in WATCHED_CM_MODELS:
        return False
    return True


class CmConfig(AppConfig):
    name = 'cm'
    model_change = partial(model_change, filter_out=filter_out_event)
    model_delete = partial(model_delete, filter_out=filter_out_event)
    m2m_change = partial(m2m_change, filter_out=filter_out_event)

    def ready(self):
        # pylint: disable-next=import-outside-toplevel,unused-import
        from cm.signals import (
            mark_deleted_audit_object_handler,
            rename_audit_object,
            rename_audit_object_host,
        )

        post_save.connect(self.model_change, dispatch_uid='model_change')
        post_delete.connect(self.model_delete, dispatch_uid='model_delete')
        m2m_changed.connect(self.m2m_change, dispatch_uid='m2m_change')
