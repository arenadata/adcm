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

from pathlib import Path

from api.config.serializers import ConfigSerializerUI
from api.utils import get_api_url_kwargs
from cm.adcm_config import get_action_variant, get_prototype_config
from cm.inventory import get_inventory_data
from cm.models import Action, PrototypeConfig, SubAction
from cm.utils import get_attr, normalize_config
from django.conf import settings
from jinja2 import Template
from rest_framework.reverse import reverse
from rest_framework.serializers import (
    BooleanField,
    CharField,
    HyperlinkedIdentityField,
    HyperlinkedModelSerializer,
    IntegerField,
    JSONField,
    SerializerMethodField,
)
from yaml import load
from yaml.loader import SafeLoader

from adcm.serializers import EmptySerializer


class ActionJobSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Action
        fields = (
            "name",
            "display_name",
            "prototype_id",
            "prototype_name",
            "prototype_type",
            "prototype_version",
        )


class ActionDetailURL(HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, _format):
        kwargs = get_api_url_kwargs(self.context.get("object"), request)
        kwargs["action_id"] = obj.id

        return reverse(view_name, kwargs=kwargs, request=request, format=_format)


class HostActionDetailURL(HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, _format):
        objects = self.context.get("objects")
        if obj.host_action and "host" in objects:
            kwargs = get_api_url_kwargs(objects["host"], request)
        else:
            kwargs = get_api_url_kwargs(objects[obj.prototype.type], request)

        kwargs["action_id"] = obj.id

        return reverse(view_name, kwargs=kwargs, request=request, format=_format)


class StackActionSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    prototype_id = IntegerField()
    name = CharField()
    type = CharField()
    display_name = CharField(required=False)
    description = CharField(required=False)
    ui_options = JSONField(required=False)
    script = CharField()
    script_type = CharField()
    state_on_success = CharField()
    state_on_fail = CharField()
    hostcomponentmap = JSONField(required=False)
    allow_to_terminate = BooleanField(read_only=True)
    partial_execution = BooleanField(read_only=True)
    host_action = BooleanField(read_only=True)
    start_impossible_reason = SerializerMethodField()

    def get_start_impossible_reason(self, action: Action):
        if self.context.get("obj"):
            return action.get_start_impossible_reason(self.context["obj"])

        return None


class ActionSerializer(StackActionSerializer):
    url = HostActionDetailURL(read_only=True, view_name="object-action-details")


class ActionShort(EmptySerializer):
    name = CharField()
    display_name = CharField(required=False)
    config = SerializerMethodField()
    hostcomponentmap = JSONField(read_only=False)
    run = ActionDetailURL(read_only=True, view_name="run-task")

    def get_config(self, obj):
        context = self.context
        context["prototype"] = obj.prototype
        _, _, _, attr = get_prototype_config(obj.prototype, obj)
        get_action_variant(context.get("object"), obj.config)
        conf = ConfigSerializerUI(obj.config, many=True, context=context, read_only=True)

        return {"attr": attr, "config": conf.data}


class SubActionSerializer(EmptySerializer):
    name = CharField()
    display_name = CharField(required=False)
    script = CharField()
    script_type = CharField()
    state_on_fail = CharField(required=False)
    params = JSONField(required=False)


class StackActionDetailSerializer(StackActionSerializer):
    state_available = JSONField()
    state_unavailable = JSONField()
    multi_state_available = JSONField()
    multi_state_unavailable = JSONField()
    params = JSONField(required=False)
    log_files = JSONField(required=False)
    config = SerializerMethodField()
    subs = SerializerMethodField()
    disabling_cause = CharField(read_only=True)

    def get_jinja_config(self, action: Action) -> tuple[list[PrototypeConfig], dict]:
        inventory_data = get_inventory_data(obj=self.context["objects"][action.prototype_type], action=action)
        jinja_conf_file = Path(settings.BUNDLE_DIR, action.prototype.bundle.hash, action.config_jinja)
        template = Template(source=jinja_conf_file.read_text(encoding=settings.ENCODING_UTF_8))
        data_yaml = template.render(inventory_data["all"]["children"]["CLUSTER"]["vars"])
        data = load(stream=data_yaml, Loader=SafeLoader)

        configs = []
        attr = {}
        for config in data:
            for normalized_config in normalize_config(config=config, root_path=action.prototype.path):
                configs.append(PrototypeConfig(prototype=action.prototype, action=action, **normalized_config))
                attr.update(**get_attr(config=normalized_config))

        return configs, attr

    def get_config(self, action: Action) -> dict:
        if action.config_jinja:
            if not self.context.get("objects"):
                return {}

            action_config, attr = self.get_jinja_config(action=action)
        else:
            action_config = PrototypeConfig.objects.filter(prototype=action.prototype, action=action).order_by("id")
            _, _, _, attr = get_prototype_config(proto=action.prototype, action=action)

        self.context["prototype"] = action.prototype
        conf = ConfigSerializerUI(instance=action_config, many=True, context=self.context, read_only=True)

        return {"attr": attr, "config": conf.data}

    def get_subs(self, obj):
        sub_actions = SubAction.objects.filter(action=obj).order_by("id")
        subs = SubActionSerializer(sub_actions, many=True, context=self.context, read_only=True)

        return subs.data


class ActionDetailSerializer(StackActionDetailSerializer):
    run = HostActionDetailURL(read_only=True, view_name="run-task")


class ActionUISerializer(ActionDetailSerializer):
    def get_config(self, action: Action) -> dict:
        if action.config_jinja:
            action_config, attr = self.get_jinja_config(action=action)
        else:
            action_config = PrototypeConfig.objects.filter(prototype=action.prototype, action=action).order_by("id")
            _, _, _, attr = get_prototype_config(proto=action.prototype, action=action)

        get_action_variant(obj=self.context["obj"], config=action_config)
        conf = ConfigSerializerUI(instance=action_config, many=True, context=self.context, read_only=True)

        return {"attr": attr, "config": conf.data}
