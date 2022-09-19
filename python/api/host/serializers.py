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

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import (
    BooleanField,
    CharField,
    ChoiceField,
    IntegerField,
    SerializerMethodField,
)
from rest_framework.validators import UniqueValidator

from adcm.serializers import EmptySerializer
from api.action.serializers import ActionShort
from api.concern.serializers import ConcernItemSerializer, ConcernItemUISerializer
from api.serializers import StringListSerializer
from api.utils import CommonAPIURL, ObjectURL, check_obj, filter_actions, hlink
from cm.adcm_config import get_main_info
from cm.api import add_host
from cm.errors import AdcmEx
from cm.issue import update_hierarchy_issues, update_issue_after_deleting
from cm.models import Action, Host, HostProvider, MaintenanceModeType, Prototype
from cm.stack import validate_name
from cm.status_api import get_host_status


class HostUniqueValidator(UniqueValidator):
    def __call__(self, value, serializer_field):
        try:
            super().__call__(value, serializer_field)
        except ValidationError as e:
            raise AdcmEx("HOST_CONFLICT", "duplicate host") from e


class HostFQDNRegexValidator(RegexValidator):
    def __call__(self, value):
        try:
            super().__call__(value)
        except DjangoValidationError as e:
            raise AdcmEx("WRONG_NAME", "host FQDN doesn't meet requirements") from e


class HostSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    cluster_id = IntegerField(read_only=True)
    prototype_id = IntegerField(help_text="id of host type")
    provider_id = IntegerField()
    fqdn = CharField(
        max_length=253,
        help_text="fully qualified domain name",
        validators=[
            HostUniqueValidator(queryset=Host.objects.all()),
            HostFQDNRegexValidator(regex=settings.REGEX_HOST_FQDN),
        ],
    )
    description = CharField(required=False, allow_blank=True)
    state = CharField(read_only=True)
    maintenance_mode = ChoiceField(choices=MaintenanceModeType.choices, read_only=True)
    url = ObjectURL(read_only=True, view_name="host-details")

    @staticmethod
    def validate_prototype_id(prototype_id):
        return check_obj(Prototype, {"id": prototype_id, "type": "host"})

    @staticmethod
    def validate_provider_id(provider_id):
        return check_obj(HostProvider, provider_id)

    @staticmethod
    def validate_fqdn(name):
        return validate_name(name, "Host name")

    def create(self, validated_data):
        return add_host(
            validated_data.get("prototype_id"),
            validated_data.get("provider_id"),
            validated_data.get("fqdn"),
            validated_data.get("description", ""),
        )


class HostDetailSerializer(HostSerializer):
    bundle_id = IntegerField(read_only=True)
    status = SerializerMethodField()
    config = CommonAPIURL(view_name="object-config")
    action = CommonAPIURL(view_name="object-action")
    prototype = hlink("host-type-details", "prototype_id", "prototype_id")
    multi_state = StringListSerializer(read_only=True)
    concerns = ConcernItemSerializer(many=True, read_only=True)
    locked = BooleanField(read_only=True)

    @staticmethod
    def get_status(obj):
        return get_host_status(obj)


class HostUpdateSerializer(HostDetailSerializer):
    maintenance_mode = ChoiceField(choices=MaintenanceModeType.choices)

    def update(self, instance, validated_data):
        instance.maintenance_mode = validated_data.get(
            "maintenance_mode", instance.maintenance_mode
        )
        instance.fqdn = validated_data.get("fqdn", instance.fqdn)
        instance.save()

        update_hierarchy_issues(instance.cluster)
        update_hierarchy_issues(instance.provider)
        update_issue_after_deleting()

        return instance


class ClusterHostSerializer(HostSerializer):
    host_id = IntegerField(source="id")
    prototype_id = IntegerField(read_only=True)
    provider_id = IntegerField(read_only=True)
    fqdn = CharField(read_only=True)


class ProvideHostSerializer(HostSerializer):
    prototype_id = IntegerField(read_only=True)
    provider_id = IntegerField(read_only=True)

    def create(self, validated_data):
        provider = check_obj(HostProvider, self.context.get("provider_id"))
        proto = Prototype.obj.get(bundle=provider.prototype.bundle, type="host")

        return add_host(
            proto, provider, validated_data.get("fqdn"), validated_data.get("description", "")
        )


class StatusSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    fqdn = CharField(read_only=True)
    status = SerializerMethodField()

    @staticmethod
    def get_status(obj):
        return get_host_status(obj)


class HostUISerializer(HostSerializer):
    action = CommonAPIURL(view_name='object-action')
    cluster_name = SerializerMethodField()
    prototype_version = SerializerMethodField()
    prototype_name = SerializerMethodField()
    prototype_display_name = SerializerMethodField()
    provider_name = SerializerMethodField()
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    locked = BooleanField(read_only=True)
    status = SerializerMethodField()

    def get_cluster_name(self, obj):
        if obj.cluster:
            return obj.cluster.name
        return None

    def get_prototype_version(self, obj):
        return obj.prototype.version

    def get_prototype_name(self, obj):
        return obj.prototype.name

    def get_prototype_display_name(self, obj):
        return obj.prototype.display_name

    def get_provider_name(self, obj):
        if obj.provider:
            return obj.provider.name
        return None

    def get_status(self, obj):
        return get_host_status(obj)


class HostDetailUISerializer(HostDetailSerializer):
    actions = SerializerMethodField()
    cluster_name = SerializerMethodField()
    prototype_version = SerializerMethodField()
    prototype_name = SerializerMethodField()
    prototype_display_name = SerializerMethodField()
    provider_name = SerializerMethodField()
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    main_info = SerializerMethodField()

    def get_actions(self, obj):
        act_set = Action.objects.filter(prototype=obj.prototype)
        self.context["object"] = obj
        self.context["host_id"] = obj.id
        actions = ActionShort(filter_actions(obj, act_set), many=True, context=self.context)

        return actions.data

    @staticmethod
    def get_cluster_name(obj):
        if obj.cluster:
            return obj.cluster.name

        return None

    @staticmethod
    def get_prototype_version(obj):
        return obj.prototype.version

    @staticmethod
    def get_prototype_name(obj):
        return obj.prototype.name

    @staticmethod
    def get_prototype_display_name(obj):
        return obj.prototype.display_name

    @staticmethod
    def get_provider_name(obj):
        if obj.provider:
            return obj.provider.name
        return None

    @staticmethod
    def get_main_info(obj):
        return get_main_info(obj)
