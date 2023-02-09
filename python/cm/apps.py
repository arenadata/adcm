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

from django.apps import AppConfig

WATCHED_CM_MODELS = (
    "group-config",
    "group-config-hosts",
    "adcm-concerns",
    "cluster-concerns",
    "cluster-object-concerns",
    "service-component-concerns",
    "host-provider-concerns",
    "host-concerns",
)
WATCHED_RBAC_MODELS = (
    "user",
    "group",
    "policy",
    "role",
)


class CmConfig(AppConfig):
    name = "cm"

    def ready(self):
        # pylint: disable-next=import-outside-toplevel,unused-import
        from cm.signals import (
            m2m_change,
            mark_deleted_audit_object_handler,
            model_change,
            model_delete,
            rename_audit_object,
            rename_audit_object_host,
        )
