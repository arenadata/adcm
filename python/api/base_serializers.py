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

from collections import OrderedDict

from django.db.models.manager import BaseManager
from rest_framework import serializers, exceptions


class ADCMBaseSerializer(serializers.ModelSerializer):
    """
    Extends rest_framework.serializers.ModelSerializer for:
    * Control that fields from `<Model>.api_not_changeable_fields`
      are create-only from API point of view
    """

    def _get_api_not_changeable_fields(self):
        api_not_changeable_fields = getattr(
            self.Meta.model, 'api_not_changeable_fields', []  # pylint: disable=no-member
        )
        if not isinstance(api_not_changeable_fields, (list, tuple)):
            raise TypeError(
                'The `<Model>.api_not_changeable_fields` attribute must be a list or tuple. '
                'Got {}.'.format(type(api_not_changeable_fields).__name__)
            )
        return api_not_changeable_fields

    def _get_instance_serialized_value(self, field_name):
        field = self.fields.fields[field_name]
        instance_value = getattr(self.instance, field_name)
        if isinstance(instance_value, BaseManager):
            instance_value = instance_value.all()
        return field.to_representation(instance_value)

    def validate(self, attrs):
        """Validate that API read-only fields was not changed"""
        if not self.context:
            return attrs

        if getattr(self.context.get('view'), 'action') not in ('update', 'partial_update'):
            return attrs

        if not self.instance:
            return attrs

        if not self.initial_data:
            return attrs

        errors = OrderedDict()

        for field_name in self._get_api_not_changeable_fields():
            if field_name not in self.initial_data:
                continue

            initial_value = self.initial_data[field_name]
            original_value = self._get_instance_serialized_value(field_name)

            if not isinstance(self.fields.fields[field_name], serializers.JSONField):
                if isinstance(initial_value, dict) and isinstance(original_value, dict):
                    initial_value = initial_value['id']
                    original_value = original_value['id']

                if isinstance(initial_value, list) and isinstance(original_value, list):
                    initial_value = {i['id'] for i in initial_value}
                    original_value = {i['id'] for i in original_value}

            if initial_value != original_value:
                errors[field_name] = 'This field cannot be changed'
        if errors:
            raise exceptions.ValidationError(errors)

        return attrs
