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

from cm.models.base import ADCMEntity, ADCMModel, Prototype
from cm.models.utils import get_default_before_upgrade


class Cluster(ADCMEntity):
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    group_config = GenericRelation(
        'GroupConfig',
        object_id_field='object_id',
        content_type_field='object_type',
        on_delete=models.CASCADE,
    )
    before_upgrade = models.JSONField(default=get_default_before_upgrade)

    __error_code__ = 'CLUSTER_NOT_FOUND'

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


class ClusterObject(ADCMEntity):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
    service = models.ForeignKey("self", on_delete=models.CASCADE, null=True, default=None)
    group_config = GenericRelation(
        'GroupConfig',
        object_id_field='object_id',
        content_type_field='object_type',
        on_delete=models.CASCADE,
    )

    __error_code__ = 'CLUSTER_SERVICE_NOT_FOUND'

    @property
    def bundle_id(self):
        return self.prototype.bundle_id

    @property
    def version(self):
        return self.prototype.version

    @property
    def name(self):
        return self.prototype.name

    @property
    def display_name(self):
        return self.prototype.display_name

    @property
    def description(self):
        return self.prototype.description

    @property
    def monitoring(self):
        return self.prototype.monitoring

    @property
    def serialized_issue(self):
        result = {
            'id': self.id,
            'name': self.display_name,
            'issue': self.issue,
        }
        return result if result['issue'] else {}

    class Meta:
        unique_together = (('cluster', 'prototype'),)


class ServiceComponent(ADCMEntity):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
    service = models.ForeignKey(ClusterObject, on_delete=models.CASCADE)
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE, null=True, default=None)
    group_config = GenericRelation(
        'GroupConfig',
        object_id_field='object_id',
        content_type_field='object_type',
        on_delete=models.CASCADE,
    )

    __error_code__ = 'COMPONENT_NOT_FOUND'

    @property
    def name(self):
        return self.prototype.name

    @property
    def display_name(self):
        return self.prototype.display_name

    @property
    def description(self):
        return self.prototype.description

    @property
    def constraint(self):
        return self.prototype.constraint

    @property
    def requires(self):
        return self.prototype.requires

    @property
    def bound_to(self):
        return self.prototype.bound_to

    @property
    def monitoring(self):
        return self.prototype.monitoring

    @property
    def serialized_issue(self):
        result = {
            'id': self.id,
            'name': self.display_name,
            'issue': self.issue,
        }
        return result if result['issue'] else {}

    class Meta:
        unique_together = (('cluster', 'service', 'prototype'),)


class ClusterBind(ADCMModel):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
    service = models.ForeignKey(ClusterObject, on_delete=models.CASCADE, null=True, default=None)
    source_cluster = models.ForeignKey(
        Cluster, related_name='source_cluster', on_delete=models.CASCADE
    )
    source_service = models.ForeignKey(
        ClusterObject,
        related_name='source_service',
        on_delete=models.CASCADE,
        null=True,
        default=None,
    )

    __error_code__ = 'BIND_NOT_FOUND'

    class Meta:
        unique_together = (('cluster', 'service', 'source_cluster', 'source_service'),)


def get_object_cluster(obj):
    if isinstance(obj, Cluster):
        return obj
    if hasattr(obj, 'cluster'):
        return obj.cluster
    else:
        return None
