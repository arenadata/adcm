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
from typing import Type, Tuple, Any

from django.db.models import Model
from rest_framework import serializers


class BaseRelatedSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        if "id" not in data:
            raise serializers.ValidationError("This field may not be empty.")
        return data["id"]


def update_m2m_field(m2m, instances) -> None:
    """
    Update m2m field for object

    :param m2m: ManyToManeField
    :type m2m: ManyRelatedManager
    :param instances: list of objects
    :type instances: list
    """
    if instances:
        m2m.clear()
        m2m.add(*instances)
    else:
        m2m.clear()


def create_model_serializer_class(
    name: str, model: Type[Model], meta_fields: Tuple[str, ...], fields: dict = None
):
    """
    Creating serializer class for model

    :param name: Name serializer class
    :param model: Model from models.py
    :param meta_fields: `fields` field from Meta class
    :param fields: Overridden fields in serializer class
    :return: Serializer class inherited from ModelSerializer
    """
    meta_class = type('Meta', (), {'model': model, 'fields': meta_fields})
    _bases = (serializers.ModelSerializer,)
    _dict = {'Meta': meta_class}

    if fields is not None:
        _dict.update(fields)

    return type(name, _bases, _dict)


class Empty:
    """Same as None but useful when None is valid value"""

    def __bool__(self):
        return False


def set_not_empty_attr(obj, partial: bool, attr: str, value: Any, default: Any = None) -> None:
    """Update object attribute if not empty in some abstract way"""
    if partial:
        if value is not Empty:
            setattr(obj, attr, value)
    else:
        value = value if value is not Empty else default
        setattr(obj, attr, value)
