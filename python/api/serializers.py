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

from adcm.serializers import EmptySerializer
from cm.adcm_config.config import get_action_variant, get_prototype_config, ui_config
from cm.errors import raise_adcm_ex
from cm.models import Cluster, ConfigHostGroup, PrototypeConfig, Provider, Upgrade
from rest_framework.reverse import reverse
from rest_framework.serializers import (
    BooleanField,
    CharField,
    HyperlinkedIdentityField,
    HyperlinkedRelatedField,
    IntegerField,
    JSONField,
    ListField,
    SerializerMethodField,
)

from api.config.serializers import ConfigSerializerUI
from api.utils import UrlField, check_obj, hlink

# TODO: remove `drf-extensions` package after merge to develop
PARENT_LOOKUP_KWARG_NAME_PREFIX = "parent_lookup_"


class UpgradeSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    name = CharField(required=False)
    display_name = CharField(read_only=True)
    bundle_id = IntegerField(read_only=True)
    description = CharField(required=False)
    min_version = CharField(required=False)
    max_version = CharField(required=False)
    min_strict = BooleanField(required=False)
    max_strict = BooleanField(required=False)
    upgradable = SerializerMethodField()
    license = CharField(required=False)
    license_url = hlink("bundle-license", "bundle_id", "bundle_pk")
    from_edition = JSONField(required=False)
    state_available = JSONField(required=False)
    state_on_success = CharField(required=False)
    ui_options = SerializerMethodField()
    config = SerializerMethodField()

    @staticmethod
    def get_ui_options(instance):
        if instance.action:
            return instance.action.ui_options
        return {}

    def get_config(self, instance):
        if instance.action is None:
            return {"attr": {}, "config": []}

        if "cluster_id" in self.context:
            obj = check_obj(Cluster, self.context["cluster_id"])
        elif "provider_id" in self.context:
            obj = check_obj(Provider, self.context["provider_id"])
        else:
            obj = None

        action_conf = PrototypeConfig.objects.filter(
            prototype=instance.action.prototype,
            action=instance.action,
        ).order_by("id")
        *_, attr = get_prototype_config(instance.action.prototype, instance.action)
        if obj:
            get_action_variant(obj, action_conf)
        conf = ConfigSerializerUI(action_conf, many=True, context=self.context, read_only=True)
        return {"attr": attr, "config": conf.data}

    def get_upgradable(self, instance: Upgrade) -> bool:  # noqa: ARG001, ARG002
        return self.context.get("upgradable", False)


class ClusterUpgradeSerializer(UpgradeSerializer):
    class MyUrlField(UrlField):
        def get_kwargs(self, obj):
            return {"cluster_id": self.context["cluster_id"], "upgrade_id": obj.id}

    hostcomponentmap = SerializerMethodField()
    url = MyUrlField(read_only=True, view_name="v1:cluster-upgrade-details")
    do = MyUrlField(read_only=True, view_name="v1:do-cluster-upgrade")

    def get_hostcomponentmap(self, instance):
        if instance.action:
            return instance.action.hostcomponentmap
        return []


class ProviderUpgradeSerializer(UpgradeSerializer):
    class MyUrlField(UrlField):
        def get_kwargs(self, obj):
            return {"provider_id": self.context["provider_id"], "upgrade_id": obj.id}

    url = MyUrlField(read_only=True, view_name="v1:provider-upgrade-details")
    do = MyUrlField(read_only=True, view_name="v1:do-provider-upgrade")


class DoUpgradeSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    upgradable = BooleanField(read_only=True)
    config = JSONField(required=False, default=dict)
    task_id = IntegerField(read_only=True)
    attr = JSONField(required=False, default=dict)


class StringListSerializer(ListField):
    item = CharField()


class UIConfigField(JSONField):
    """Serializing config field for UI"""

    def to_representation(self, value):
        obj = value.obj_ref.object
        if obj is None:
            raise_adcm_ex("INVALID_CONFIG_UPDATE", f'unknown object type "{value.obj_ref}"')
        if isinstance(obj, ConfigHostGroup):
            obj = obj.object
        return ui_config(obj, value)

    def to_internal_value(self, data):
        return {"config": data}


class MultiHyperlinkedIdentityField(HyperlinkedIdentityField):
    """
    Hyperlinked identity field for nested routers
    """

    def __init__(self, view_name, *args, **kwargs):
        self.url_args = args
        super().__init__(view_name=view_name, **kwargs)

    def get_url(self, obj, view_name, request, _format):
        kwargs = {}
        for url_arg in self.url_args:
            if url_arg.startswith(PARENT_LOOKUP_KWARG_NAME_PREFIX):
                parent_name = url_arg.replace(PARENT_LOOKUP_KWARG_NAME_PREFIX, "", 1)
                parent = self.context.get(parent_name)
                kwargs.update({url_arg: parent.id})
            else:
                kwargs.update({url_arg: obj.id})
        return reverse(viewname=view_name, kwargs=kwargs, request=request, format=_format)


class MultiHyperlinkedRelatedField(HyperlinkedRelatedField):
    """
    Hyperlinked related field for nested routers
    """

    def __init__(self, view_name, *args, **kwargs):
        kwargs["read_only"] = True
        self.url_args = args
        super().__init__(view_name, **kwargs)

    def get_url(self, obj, view_name, request, _format):
        kwargs = {}
        for url_arg in self.url_args:
            if url_arg.startswith(PARENT_LOOKUP_KWARG_NAME_PREFIX):
                parent_name = url_arg.replace(PARENT_LOOKUP_KWARG_NAME_PREFIX, "", 1)
                parent = self.context.get(parent_name)
                if parent is None:
                    parent = obj
                kwargs.update({url_arg: parent.id})
        lookup_value = getattr(obj, self.lookup_field)
        if lookup_value is None:
            return lookup_value
        kwargs.update({self.lookup_url_kwarg: lookup_value})
        return reverse(viewname=view_name, kwargs=kwargs, request=request, format=_format)
