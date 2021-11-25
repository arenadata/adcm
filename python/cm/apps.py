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

from adwp_events.signals import model_change, model_delete, m2m_change
from django.apps import AppConfig
from django.db.models.signals import post_save, post_delete, m2m_changed


WATCHED_CM_MODELS = (
    # 'cluster',
    'group-config',
    'group-config-hosts',
    'adcm-concerns',
    'cluster-concerns',
    'cluster-object-concerns',
    'service-component-concerns',
    'host-provider-concerns',
    'host-concerns',
)


def filter_out_event(module, name):
    # We filter the sending of events only for cm, rbac and django.contrib.auth applications
    if module in ['rbac.models', 'django.contrib.auth.models']:
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
        post_save.connect(self.model_change, dispatch_uid='model_change')
        post_delete.connect(self.model_delete, dispatch_uid='model_delete')
        m2m_changed.connect(self.m2m_change, dispatch_uid='m2m_change')
