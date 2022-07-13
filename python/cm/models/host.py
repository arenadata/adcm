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

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models

from cm.models.base import ADCMEntity, ADCMModel
from cm.models.cluster import Cluster, ClusterObject, ServiceComponent
from cm.models.types import MaintenanceModeType
from cm.models.utils import get_default_before_upgrade


class HostProvider(ADCMEntity):
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    group_config = GenericRelation(
        'GroupConfig',
        object_id_field='object_id',
        content_type_field='object_type',
        on_delete=models.CASCADE,
    )
    before_upgrade = models.JSONField(default=get_default_before_upgrade)

    __error_code__ = 'PROVIDER_NOT_FOUND'

    @property
    def bundle_id(self):
        return self.prototype.bundle_id

    @property
    def edition(self):
        return self.prototype.bundle.edition

    @property
    def license(self):
        return self.prototype.bundle.license

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


class Host(ADCMEntity):
    fqdn = models.CharField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    provider = models.ForeignKey(HostProvider, on_delete=models.CASCADE, null=True, default=None)
    cluster = models.ForeignKey(Cluster, on_delete=models.SET_NULL, null=True, default=None)
    maintenance_mode = models.CharField(
        max_length=16,
        choices=MaintenanceModeType.choices,
        default=MaintenanceModeType.Disabled.value,
    )

    __error_code__ = 'HOST_NOT_FOUND'

    @property
    def bundle_id(self):
        return self.prototype.bundle_id

    @property
    def monitoring(self):
        return self.prototype.monitoring

    @property
    def display_name(self):
        return self.fqdn

    @property
    def serialized_issue(self):
        result = {'id': self.id, 'name': self.fqdn, 'issue': self.issue.copy()}
        provider_issue = self.provider.serialized_issue
        if provider_issue:
            result['issue']['provider'] = provider_issue
        return result if result['issue'] else {}


class HostComponent(ADCMModel):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    service = models.ForeignKey(ClusterObject, on_delete=models.CASCADE)
    component = models.ForeignKey(ServiceComponent, on_delete=models.CASCADE)
    state = models.CharField(max_length=64, default='created')

    class Meta:
        unique_together = (('host', 'service', 'component'),)