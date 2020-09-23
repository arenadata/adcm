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

import django.contrib.auth
import rest_framework.authtoken.serializers
from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework.reverse import reverse

import cm.config as config
import cm.job
import cm.stack
import cm.status_api
import cm.adcm_config
from cm.api import safe_api
from cm.errors import AdcmApiEx, AdcmEx
from cm.models import (
    Action, SubAction, Prototype, PrototypeConfig, JobLog, UserProfile, Upgrade, HostProvider,
    ConfigLog, Role, Host, Cluster, ClusterObject
)
from api.config.serializers import ConfigURL


def check_obj(model, req, error):
    if isinstance(req, dict):
        kw = req
    else:
        kw = {'id': req}
    try:
        return model.objects.get(**kw)
    except model.DoesNotExist:
        raise AdcmApiEx(error) from None


def get_upgradable_func(self, obj):
    return bool(cm.upgrade.get_upgrade(obj))


def filter_actions(obj, actions_set):
    if obj.state == config.Job.LOCKED:
        return []
    filtered = []
    for act in actions_set:
        available = act.state_available
        if available == 'any':
            filtered.append(act)
        elif obj.state in available:
            filtered.append(act)
    for act in actions_set:
        act.config = PrototypeConfig.objects.filter(
            prototype=act.prototype, action=act
        ).order_by('id')
    return filtered


def get_config_version(objconf, version):
    if version == 'previous':
        ver = objconf.previous
    elif version == 'current':
        ver = objconf.current
    else:
        ver = version
    try:
        cl = ConfigLog.objects.get(obj_ref=objconf, id=ver)
    except ConfigLog.DoesNotExist:
        raise AdcmApiEx('CONFIG_NOT_FOUND', "config version doesn't exist") from None
    return cl


def hlink(view, lookup, lookup_url):
    return serializers.HyperlinkedIdentityField(
        view_name=view, lookup_field=lookup, lookup_url_kwarg=lookup_url
    )


class DataField(serializers.CharField):
    def to_representation(self, value):
        return value


class UrlField(serializers.HyperlinkedIdentityField):
    def get_kwargs(self, obj):
        return {}

    def get_url(self, obj, view_name, request, format):		# pylint: disable=redefined-builtin
        kwargs = self.get_kwargs(obj)
        return reverse(self.view_name, kwargs=kwargs, request=request, format=format)


class AuthSerializer(rest_framework.authtoken.serializers.AuthTokenSerializer):
    def validate(self, attrs):
        user = django.contrib.auth.authenticate(
            username=attrs.get('username'),
            password=attrs.get('password')
        )
        if not user:
            raise AdcmApiEx('AUTH_ERROR', 'Wrong user or password')
        attrs['user'] = user
        return attrs


class LogOutSerializer(serializers.Serializer):
    pass


class PermSerializer(serializers.Serializer):
    name = serializers.CharField()
    codename = serializers.CharField()
    app_label = serializers.SerializerMethodField()
    model = serializers.SerializerMethodField()

    def get_app_label(self, obj):
        return obj.content_type.app_label

    def get_model(self, obj):
        return obj.content_type.model


class RoleSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    url = hlink('role-details', 'id', 'role_id')


class RoleDetailSerializer(RoleSerializer):
    permissions = PermSerializer(many=True, read_only=True)


class GroupSerializer(serializers.Serializer):
    name = serializers.CharField()
    url = hlink('group-details', 'name', 'name')
    change_role = hlink('change-group-role', 'name', 'name')

    @transaction.atomic
    def create(self, validated_data):
        try:
            return Group.objects.create(name=validated_data.get('name'))
        except IntegrityError:
            raise AdcmApiEx("GROUP_CONFLICT", 'group already exists') from None


class GroupDetailSerializer(GroupSerializer):
    permissions = PermSerializer(many=True, read_only=True)
    role = RoleSerializer(many=True, source='role_set')


class UserSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    url = hlink('user-details', 'username', 'username')
    change_group = hlink('add-user-group', 'username', 'username')
    change_password = hlink('user-passwd', 'username', 'username')
    change_role = hlink('change-user-role', 'username', 'username')
    is_superuser = serializers.BooleanField(required=False)

    @transaction.atomic
    def create(self, validated_data):
        try:
            user = User.objects.create_user(
                validated_data.get('username'),
                password=validated_data.get('password'),
                is_superuser=validated_data.get('is_superuser', True)
            )
            UserProfile.objects.create(login=validated_data.get('username'))
            return user
        except IntegrityError:
            raise AdcmApiEx("USER_CONFLICT", 'user already exists') from None


class UserDetailSerializer(UserSerializer):
    user_permissions = PermSerializer(many=True)
    groups = GroupSerializer(many=True)
    role = RoleSerializer(many=True, source='role_set')


class AddUser2GroupSerializer(serializers.Serializer):
    name = serializers.CharField()

    def update(self, user, validated_data):   # pylint: disable=arguments-differ
        group = check_obj(Group, {'name': validated_data.get('name')}, 'GROUP_NOT_FOUND')
        group.user_set.add(user)
        return group


class AddUserRoleSerializer(serializers.Serializer):
    role_id = serializers.IntegerField()
    name = serializers.CharField(read_only=True)

    def update(self, user, validated_data):   # pylint: disable=arguments-differ
        role = check_obj(Role, {'id': validated_data.get('role_id')}, 'ROLE_NOT_FOUND')
        return safe_api(cm.api.add_user_role, (user, role))


class AddGroupRoleSerializer(serializers.Serializer):
    role_id = serializers.IntegerField()
    name = serializers.CharField(read_only=True)

    def update(self, group, validated_data):   # pylint: disable=arguments-differ
        role = check_obj(Role, {'id': validated_data.get('role_id')}, 'ROLE_NOT_FOUND')
        return safe_api(cm.api.add_group_role, (group, role))


class UserPasswdSerializer(serializers.Serializer):
    token = serializers.CharField(read_only=True, source='key')
    password = serializers.CharField(write_only=True)

    @transaction.atomic
    def update(self, user, validated_data):   # pylint: disable=arguments-differ
        user.set_password(validated_data.get('password'))
        user.save()
        token = Token.objects.get(user=user)
        token.delete()
        token.key = token.generate_key()
        token.user = user
        token.save()
        return token


class ProfileDetailSerializer(serializers.Serializer):
    class MyUrlField(UrlField):
        def get_kwargs(self, obj):
            return {'username': obj.login}

    username = serializers.CharField(read_only=True, source='login')
    change_password = MyUrlField(read_only=True, view_name='profile-passwd')
    profile = serializers.JSONField()

    def validate_profile(self, raw):
        if isinstance(raw, str):
            raise AdcmApiEx('JSON_ERROR', 'profile should not be just one string')
        return raw

    def update(self, instance, validated_data):
        instance.profile = validated_data.get('profile', instance.profile)
        try:
            instance.save()
        except IntegrityError:
            raise AdcmApiEx("USER_CONFLICT") from None
        return instance


class ProfileSerializer(ProfileDetailSerializer):
    username = serializers.CharField(source='login')
    url = hlink('profile-details', 'login', 'username')

    def create(self, validated_data):
        check_obj(User, {'username': validated_data.get('login')}, 'USER_NOT_FOUND')
        try:
            return UserProfile.objects.create(**validated_data)
        except IntegrityError:
            raise AdcmApiEx("USER_CONFLICT") from None


class EmptySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)


class AdcmSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    prototype_id = serializers.IntegerField()
    state = serializers.CharField(read_only=True)
    url = hlink('adcm-details', 'id', 'adcm_id')


class AdcmDetailSerializer(AdcmSerializer):
    prototype_version = serializers.SerializerMethodField()
    bundle_id = serializers.SerializerMethodField()
    config = ConfigURL(view_name='config')

    def get_prototype_version(self, obj):
        return obj.prototype.version

    def get_bundle_id(self, obj):
        return obj.prototype.bundle.id


class ProviderSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    prototype_id = serializers.IntegerField()
    description = serializers.CharField(required=False)
    state = serializers.CharField(read_only=True)
    url = hlink('provider-details', 'id', 'provider_id')

    def validate_prototype_id(self, prototype_id):
        proto = check_obj(
            Prototype, {'id': prototype_id, 'type': 'provider'}, "PROTOTYPE_NOT_FOUND"
        )
        return proto

    def create(self, validated_data):
        try:
            return cm.api.add_host_provider(
                validated_data.get('prototype_id'),
                validated_data.get('name'),
                validated_data.get('description', '')
            )
        except Prototype.DoesNotExist:
            raise AdcmApiEx('PROTOTYPE_NOT_FOUND') from None
        except IntegrityError:
            raise AdcmApiEx("PROVIDER_CONFLICT") from None
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code) from e


class ProviderDetailSerializer(ProviderSerializer):
    issue = serializers.SerializerMethodField()
    edition = serializers.SerializerMethodField()
    license = serializers.SerializerMethodField()
    bundle_id = serializers.SerializerMethodField()
    prototype = hlink('provider-type-details', 'prototype_id', 'prototype_id')
    config = ConfigURL(view_name='config')
    action = hlink('provider-action', 'id', 'provider_id')
    upgrade = hlink('provider-upgrade', 'id', 'provider_id')
    host = hlink('provider-host', 'id', 'provider_id')

    def get_issue(self, obj):
        return cm.issue.get_issue(obj)

    def get_bundle_id(self, obj):
        return obj.prototype.bundle_id

    def get_edition(self, obj):
        return obj.prototype.bundle.edition

    def get_license(self, obj):
        return obj.prototype.bundle.license


class ProviderUISerializer(ProviderDetailSerializer):
    actions = serializers.SerializerMethodField()
    prototype_version = serializers.SerializerMethodField()
    prototype_name = serializers.SerializerMethodField()
    prototype_display_name = serializers.SerializerMethodField()
    upgradable = serializers.SerializerMethodField()
    get_upgradable = get_upgradable_func

    def get_actions(self, obj):
        act_set = Action.objects.filter(prototype=obj.prototype)
        self.context['object'] = obj
        self.context['provider_id'] = obj.id
        actions = ProviderActionShort(filter_actions(obj, act_set), many=True, context=self.context)
        return actions.data

    def get_prototype_version(self, obj):
        return obj.prototype.version

    def get_prototype_name(self, obj):
        return obj.prototype.name

    def get_prototype_display_name(self, obj):
        return obj.prototype.display_name


class HostSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    cluster_id = serializers.IntegerField(read_only=True)
    prototype_id = serializers.IntegerField(help_text='id of host type')
    provider_id = serializers.IntegerField()
    fqdn = serializers.CharField(help_text='fully qualified domain name')
    description = serializers.CharField(required=False)
    state = serializers.CharField(read_only=True)
    url = hlink('host-details', 'id', 'host_id')

    def get_issue(self, obj):
        return cm.issue.get_issue(obj)

    def validate_prototype_id(self, prototype_id):
        proto = check_obj(
            Prototype, {'id': prototype_id, 'type': 'host'}, "PROTOTYPE_NOT_FOUND"
        )
        return proto

    def validate_provider_id(self, provider_id):
        provider = check_obj(HostProvider, provider_id, "PROVIDER_NOT_FOUND")
        return provider

    def validate_fqdn(self, name):
        try:
            return cm.stack.validate_name(name, 'Host name')
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code) from e

    def create(self, validated_data):
        try:
            return cm.api.add_host(
                validated_data.get('prototype_id'),
                validated_data.get('provider_id'),
                validated_data.get('fqdn'),
                validated_data.get('description', '')
            )
        except Prototype.DoesNotExist:
            raise AdcmApiEx('PROTOTYPE_NOT_FOUND') from None
        except IntegrityError:
            raise AdcmApiEx("HOST_CONFLICT", "duplicate host") from None
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code) from e

    def update(self, instance, validated_data):
        instance.cluster_id = validated_data.get('cluster_id')
        instance.save()
        return instance


class HostDetailSerializer(HostSerializer):
    # stack = serializers.JSONField(read_only=True)
    issue = serializers.SerializerMethodField()
    bundle_id = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    config = ConfigURL(view_name='config')
    action = hlink('host-action', 'id', 'host_id')
    prototype = hlink('host-type-details', 'prototype_id', 'prototype_id')

    def get_issue(self, obj):
        return cm.issue.get_issue(obj)

    def get_bundle_id(self, obj):
        return obj.prototype.bundle_id

    def get_status(self, obj):
        return cm.status_api.get_host_status(obj.id)


class HostUISerializer(HostDetailSerializer):
    actions = serializers.SerializerMethodField()
    cluster_name = serializers.SerializerMethodField()
    prototype_version = serializers.SerializerMethodField()
    prototype_name = serializers.SerializerMethodField()
    prototype_display_name = serializers.SerializerMethodField()
    provider_name = serializers.SerializerMethodField()

    def get_actions(self, obj):
        act_set = Action.objects.filter(prototype=obj.prototype)
        self.context['object'] = obj
        self.context['host_id'] = obj.id
        actions = HostActionShort(filter_actions(obj, act_set), many=True, context=self.context)
        return actions.data

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


class ProviderHostSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    cluster_id = serializers.IntegerField(read_only=True)
    prototype_id = serializers.IntegerField(required=False, read_only=True)
    provider_id = serializers.IntegerField(required=False, read_only=True)
    fqdn = serializers.CharField(help_text='fully qualified domain name')
    description = serializers.CharField(required=False)
    state = serializers.CharField(read_only=True)
    # stack = serializers.JSONField(read_only=True)
    url = hlink('host-details', 'id', 'host_id')

    def validate_fqdn(self, name):
        try:
            return cm.stack.validate_name(name, 'Host name')
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code) from e

    def create(self, validated_data):
        provider = validated_data.get('provider')
        try:
            proto = Prototype.objects.get(bundle=provider.prototype.bundle, type='host')
        except Prototype.DoesNotExist:
            raise AdcmApiEx('PROTOTYPE_NOT_FOUND') from None
        try:
            return cm.api.add_host(
                proto,
                self.context.get('provider'),
                validated_data.get('fqdn'),
                validated_data.get('description', '')
            )
        except IntegrityError:
            raise AdcmApiEx("HOST_CONFLICT", "duplicate host") from None
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code) from e


class ConfigSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField(required=False)
    display_name = serializers.CharField(required=False)
    subname = serializers.CharField()
    default = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    type = serializers.CharField()
    limits = serializers.JSONField(required=False)
    ui_options = serializers.JSONField(required=False)
    required = serializers.BooleanField()

    def get_default(self, obj):   # pylint: disable=arguments-differ
        return cm.adcm_config.get_default(obj)

    def get_value(self, obj):     # pylint: disable=arguments-differ
        proto = self.context.get('prototype', None)
        return cm.adcm_config.get_default(obj, proto)


class ConfigSerializerUI(ConfigSerializer):
    activatable = serializers.SerializerMethodField()

    def get_activatable(self, obj):
        return bool(cm.adcm_config.group_is_activatable(obj))


class ActionSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    prototype_id = serializers.IntegerField()
    name = serializers.CharField()
    type = serializers.CharField()
    display_name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    ui_options = serializers.JSONField(required=False)
    button = serializers.CharField(required=False)
    script = serializers.CharField()
    script_type = serializers.CharField()
    state_on_success = serializers.CharField()
    state_on_fail = serializers.CharField()
    hostcomponentmap = serializers.JSONField(required=False)
    allow_to_terminate = serializers.BooleanField(read_only=True)
    partial_execution = serializers.BooleanField(read_only=True)


class SubActionSerializer(serializers.Serializer):
    name = serializers.CharField()
    display_name = serializers.CharField(required=False)
    script = serializers.CharField()
    script_type = serializers.CharField()
    state_on_fail = serializers.CharField(required=False)
    params = serializers.JSONField(required=False)


class ActionDetailSerializer(ActionSerializer):
    state_available = serializers.JSONField()
    params = serializers.JSONField(required=False)
    log_files = serializers.JSONField(required=False)
    config = serializers.SerializerMethodField()
    subs = serializers.SerializerMethodField()

    def get_config(self, obj):
        aconf = PrototypeConfig.objects.filter(prototype=obj.prototype, action=obj).order_by('id')
        context = self.context
        context['prototype'] = obj.prototype
        conf = ConfigSerializerUI(aconf, many=True, context=context, read_only=True)
        _, _, _, attr = cm.adcm_config.get_prototype_config(obj.prototype, obj)
        return {'attr': attr, 'config': conf.data}

    def get_subs(self, obj):
        sub_actions = SubAction.objects.filter(action=obj).order_by('id')
        subs = SubActionSerializer(sub_actions, many=True, context=self.context, read_only=True)
        return subs.data


class ClusterServiceActionUrlField(UrlField):
    def get_url(self, obj, view_name, request, format):		# pylint: disable=redefined-builtin
        kwargs = {
            'cluster_id': self.context['cluster_id'],
            'service_id': self.context['service_id'],
            'action_id': obj.id,
        }
        return reverse(self.view_name, kwargs=kwargs, request=request, format=format)


class ClusterHostActionUrlField(UrlField):
    def get_url(self, obj, view_name, request, format):		# pylint: disable=redefined-builtin
        kwargs = {
            'cluster_id': self.context['cluster_id'],
            'host_id': self.context['host_id'],
            'action_id': obj.id,
        }
        return reverse(self.view_name, kwargs=kwargs, request=request, format=format)


class ClusterServiceActionList(ActionSerializer):
    url = ClusterServiceActionUrlField(read_only=True, view_name='cluster-service-action-details')


class ClusterServiceActionDetail(ActionDetailSerializer):
    run = ClusterServiceActionUrlField(read_only=True, view_name='cluster-service-action-run')


class ClusterActionUrlField(UrlField):
    def get_kwargs(self, obj):
        return {'cluster_id': self.context['cluster_id'], 'action_id': obj.id}


class ClusterActionList(ActionSerializer):
    url = ClusterActionUrlField(read_only=True, view_name='cluster-action-details')


class ClusterActionDetail(ActionDetailSerializer):
    run = ClusterActionUrlField(read_only=True, view_name='cluster-action-run')


class ProviderActionUrlField(UrlField):
    def get_kwargs(self, obj):
        return {'provider_id': self.context['provider_id'], 'action_id': obj.id}


class ProviderActionDetail(ActionDetailSerializer):
    run = ProviderActionUrlField(read_only=True, view_name='provider-action-run')


class ProviderActionList(ActionSerializer):
    url = ProviderActionUrlField(read_only=True, view_name='provider-action-details')


class ADCMActionUrlField(UrlField):
    def get_kwargs(self, obj):
        return {'adcm_id': self.context['adcm_id'], 'action_id': obj.id}


class ADCMActionList(ActionSerializer):
    url = ADCMActionUrlField(read_only=True, view_name='adcm-action-details')


class ADCMActionDetail(ActionDetailSerializer):
    run = ADCMActionUrlField(read_only=True, view_name='adcm-action-run')


class HostActionUrlField(UrlField):
    def get_kwargs(self, obj):
        return {'host_id': self.context['host_id'], 'action_id': obj.id}


class HostActionDetail(ActionDetailSerializer):
    run = HostActionUrlField(read_only=True, view_name='host-action-run')


class HostActionList(ActionSerializer):
    url = HostActionUrlField(read_only=True, view_name='host-action-details')


class ClusterHostActionDetail(ActionDetailSerializer):
    run = ClusterHostActionUrlField(read_only=True, view_name='cluster-host-action-run')


class ClusterHostActionList(ActionSerializer):
    url = ClusterHostActionUrlField(read_only=True, view_name='cluster-host-action-details')


class ActionShort(serializers.Serializer):
    name = serializers.CharField()
    display_name = serializers.CharField(required=False)
    button = serializers.CharField(required=False)
    config = serializers.SerializerMethodField()
    hostcomponentmap = serializers.JSONField(read_only=False)

    def get_config(self, obj):
        context = self.context
        context['prototype'] = obj.prototype
        _, _, _, attr = cm.adcm_config.get_prototype_config(obj.prototype, obj)
        cm.adcm_config.get_action_variant(context.get('object'), obj.config)
        conf = ConfigSerializerUI(obj.config, many=True, context=context, read_only=True)
        return {'attr': attr, 'config': conf.data}


class ServiceActionShort(ActionShort):
    run = ClusterServiceActionUrlField(read_only=True, view_name='cluster-service-action-run')


class ClusterActionShort(ActionShort):
    run = ClusterActionUrlField(read_only=True, view_name='cluster-action-run')


class ClusterHostActionShort(ActionShort):
    run = ClusterHostActionUrlField(read_only=True, view_name='cluster-host-action-run')


class HostActionShort(ActionShort):
    run = HostActionUrlField(read_only=True, view_name='host-action-run')


class ProviderActionShort(ActionShort):
    run = ProviderActionUrlField(read_only=True, view_name='provider-action-run')


class UpgradeSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(required=False)
    bundle_id = serializers.IntegerField(read_only=True)
    description = serializers.CharField(required=False)
    min_version = serializers.CharField(required=False)
    max_version = serializers.CharField(required=False)
    min_strict = serializers.BooleanField(required=False)
    max_strict = serializers.BooleanField(required=False)
    upgradable = serializers.BooleanField(required=False)
    license = serializers.CharField(required=False)
    license_url = hlink('bundle-license', 'bundle_id', 'bundle_id')
    from_edition = serializers.JSONField(required=False)
    state_available = serializers.JSONField(required=False)
    state_on_success = serializers.CharField(required=False)


class UpgradeLinkSerializer(UpgradeSerializer):
    class MyUrlField(UrlField):
        def get_kwargs(self, obj):
            return {'cluster_id': self.context['cluster_id'], 'upgrade_id': obj.id}

    url = MyUrlField(read_only=True, view_name='cluster-upgrade-details')
    do = MyUrlField(read_only=True, view_name='do-cluster-upgrade')


class UpgradeProviderSerializer(UpgradeSerializer):
    class MyUrlField(UrlField):
        def get_kwargs(self, obj):
            return {'provider_id': self.context['provider_id'], 'upgrade_id': obj.id}

    url = MyUrlField(read_only=True, view_name='provider-upgrade-details')
    do = MyUrlField(read_only=True, view_name='do-provider-upgrade')


class DoUpgradeSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    upgradable = serializers.BooleanField(read_only=True)

    def create(self, validated_data):
        try:
            upgrade = check_obj(Upgrade, validated_data.get('upgrade_id'), 'UPGRADE_NOT_FOUND')
            return cm.upgrade.do_upgrade(validated_data.get('obj'), upgrade)
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code) from e


class StatsSerializer(serializers.Serializer):
    task = hlink('task-stats', 'id', 'task_id')
    job = hlink('job-stats', 'id', 'job_id')


def get_job_action(obj):
    try:
        act = Action.objects.get(id=obj.action_id)
        return {
            'name': act.name,
            'display_name': act.display_name,
            'prototype_id': act.prototype.id,
            'prototype_name': act.prototype.name,
            'prototype_version': act.prototype.version,
            'prototype_type': act.prototype.type,
        }
    except Action.DoesNotExist:
        return None


def get_job_objects(obj):
    resp = []
    selector = obj.selector
    for obj_type in selector:
        try:
            if obj_type == 'cluster':
                cluster = Cluster.objects.get(id=selector[obj_type])
                name = cluster.name
            elif obj_type == 'service':
                service = ClusterObject.objects.get(id=selector[obj_type])
                name = service.prototype.display_name
            elif obj_type == 'provider':
                provider = HostProvider.objects.get(id=selector[obj_type])
                name = provider.name
            elif obj_type == 'host':
                host = Host.objects.get(id=selector[obj_type])
                name = host.fqdn
            else:
                name = ''
        except ObjectDoesNotExist:
            name = 'does not exist'
        resp.append({
            'type': obj_type,
            'id': selector[obj_type],
            'name': name,
        })
    return resp


def get_job_object_type(obj):
    try:
        action = Action.objects.get(id=obj.action_id)
        return action.prototype.type
    except Action.DoesNotExist:
        return None


class TaskListSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    pid = serializers.IntegerField(read_only=True)
    object_id = serializers.IntegerField(read_only=True)
    action_id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    start_date = serializers.DateTimeField(read_only=True)
    finish_date = serializers.DateTimeField(read_only=True)
    url = hlink('task-details', 'id', 'task_id')


class JobShort(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    start_date = serializers.DateTimeField(read_only=True)
    finish_date = serializers.DateTimeField(read_only=True)
    url = hlink('job-details', 'id', 'job_id')


class TaskSerializer(TaskListSerializer):
    selector = serializers.JSONField(read_only=True)
    config = serializers.JSONField(required=False)
    attr = serializers.JSONField(required=False)
    hc = serializers.JSONField(required=False)
    hosts = serializers.JSONField(required=False)
    action_url = serializers.HyperlinkedIdentityField(
        read_only=True,
        view_name='action-details',
        lookup_field='action_id',
        lookup_url_kwarg='action_id'
    )
    action = serializers.SerializerMethodField()
    objects = serializers.SerializerMethodField()
    jobs = serializers.SerializerMethodField()
    restart = hlink('task-restart', 'id', 'task_id')
    terminatable = serializers.SerializerMethodField()
    cancel = hlink('task-cancel', 'id', 'task_id')
    object_type = serializers.SerializerMethodField()

    def get_terminatable(self, obj):
        try:
            action = Action.objects.get(id=obj.action_id)
            allow_to_terminate = action.allow_to_terminate
        except Action.DoesNotExist:
            allow_to_terminate = False
        # pylint: disable=simplifiable-if-statement
        if allow_to_terminate and obj.status in [config.Job.CREATED, config.Job.RUNNING]:
            # pylint: enable=simplifiable-if-statement
            return True
        else:
            return False

    def get_jobs(self, obj):
        task_jobs = JobLog.objects.filter(task_id=obj.id)
        for job in task_jobs:
            if job.sub_action_id:
                try:
                    sub = SubAction.objects.get(id=job.sub_action_id)
                    job.display_name = sub.display_name
                    job.name = sub.name
                except SubAction.DoesNotExist:
                    job.display_name = None
                    job.name = None
            else:
                try:
                    action = Action.objects.get(id=job.action_id)
                    job.display_name = action.display_name
                    job.name = action.name
                except Action.DoesNotExist:
                    job.display_name = None
                    job.name = None
        jobs = JobShort(task_jobs, many=True, context=self.context)
        return jobs.data

    def get_action(self, obj):
        return get_job_action(obj)

    def get_objects(self, obj):
        return get_job_objects(obj)

    def get_object_type(self, obj):
        return get_job_object_type(obj)


class TaskRunSerializer(TaskSerializer):
    def create(self, validated_data):
        try:
            obj = cm.job.start_task(
                validated_data.get('action_id'),
                validated_data.get('selector'),
                validated_data.get('config', {}),
                validated_data.get('attr', {}),
                validated_data.get('hc', []),
                validated_data.get('hosts', [])
            )
            obj.jobs = JobLog.objects.filter(task_id=obj.id)
            return obj
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code, e.adds) from e


class TaskPostSerializer(TaskRunSerializer):
    action_id = serializers.IntegerField()
    selector = serializers.JSONField()

    def validate_selector(self, selector):
        if not isinstance(selector, dict):
            raise AdcmApiEx('JSON_ERROR', 'selector should be a map')
        return selector
