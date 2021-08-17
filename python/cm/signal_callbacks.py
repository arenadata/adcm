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

"""
Django ORM signal callbacks
https://docs.djangoproject.com/en/3.2/topics/signals/
https://docs.djangoproject.com/en/3.2/ref/signals/

Was separated from models due to cyclic imports and to reduce length of code.
"""

from django.db.models import signals

from cm import models
from cm.api_context import ctx


def on_concern_change(sender, **kwargs):
    assert 'action' in kwargs
    action = kwargs.get('action')
    if action not in ('post_add', 'pre_remove'):
        return

    assert 'instance' in kwargs
    instance = kwargs['instance']
    assert isinstance(instance, models.ADCMEntity)

    assert 'model' in kwargs
    assert kwargs['model'] == models.ConcernItem

    ctx.event.change_concern(instance)


signals.m2m_changed.connect(on_concern_change, sender=models.ADCM.concerns.through)
signals.m2m_changed.connect(on_concern_change, sender=models.Cluster.concerns.through)
signals.m2m_changed.connect(on_concern_change, sender=models.ClusterObject.concerns.through)
signals.m2m_changed.connect(on_concern_change, sender=models.ServiceComponent.concerns.through)
signals.m2m_changed.connect(on_concern_change, sender=models.HostProvider.concerns.through)
signals.m2m_changed.connect(on_concern_change, sender=models.Host.concerns.through)


def on_concern_item_delete(sender, **kwargs):
    assert 'instance' in kwargs
    instance = kwargs['instance']
    assert isinstance(instance, models.ConcernItem)

    for obj in instance.related_objects:
        obj.remove_from_concerns(instance)  # to issue `change_concern` events


signals.pre_delete.connect(on_concern_item_delete, sender=models.ConcernItem)
