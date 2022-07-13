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

# pylint: disable=too-many-lines,unsupported-membership-test,unsupported-delete-operation,
# too-many-instance-attributes
# pylint could not understand that JSON fields are dicts

from __future__ import unicode_literals

from django.db import models

from cm.models.base import ADCMEntity, ADCMModel
from cm.models.cluster import Cluster, ClusterObject, ServiceComponent
from cm.models.host import Host, HostProvider


def get_model_by_type(object_type):
    if object_type == 'adcm':
        return ADCM
    if object_type == 'cluster':
        return Cluster
    elif object_type == 'provider':
        return HostProvider
    elif object_type == 'service':
        return ClusterObject
    elif object_type == 'component':
        return ServiceComponent
    elif object_type == 'host':
        return Host
    else:
        # This function should return a Model, this is necessary for the correct
        # construction of the schema.
        return Cluster


class ADCM(ADCMEntity):
    name = models.CharField(max_length=16, choices=(('ADCM', 'ADCM'),), unique=True)

    @property
    def bundle_id(self):
        return self.prototype.bundle_id

    @property
    def display_name(self):
        return self.name

    @property
    def serialized_issue(self):
        result = {
            'id': self.id,
            'name': self.name,
            'issue': self.issue,
        }
        return result if result['issue'] else {}


class UserProfile(ADCMModel):
    login = models.CharField(max_length=32, unique=True)
    profile = models.JSONField(default=str)
