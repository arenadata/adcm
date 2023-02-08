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

"""Module contains all field types and it special values"""
import random
import warnings
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timedelta
from random import choice, randint
from typing import ClassVar, List, NamedTuple, Optional, Type, Union

import attr
from multipledispatch import dispatch

# There is no circular import, because the import of the module is not yet completed at the moment,
# and this allows you to resolve the conflict.
from tests.api.utils import data_classes  # pylint: disable=unused-import,cyclic-import
from tests.api.utils.fake_data import gen_string, generate_json_from_schema
from tests.api.utils.tools import random_string


def random_json():
    """Generating json with random key values"""
    return {"int": randint(1, 100), "str": random_string()}


def random_datetime():
    """Generating datetime"""
    return (datetime.now() + timedelta(randint(-1000, 1000))).strftime("%Y-%m-%dT%H:%M:%SZ")


@attr.dataclass
class PreparedFieldValue:  # pylint: disable=function-redefined
    """
    PreparedFieldValue is object for body testing. Used for both positive and negative cases.

    An important object for generating test data, since it contains a description of what needs
    to be done with field value and what we expect as a result of sending it in body.


    value: Value to be set for field
    error_messages: Expected error message
    drop_key: If True, key in body request will be dropped
    f_type: Field type. Affects value generation

    generated_value: if True, value will be generated according to field type rules
                     when PreparedFieldValue value is requested via 'return_value' method
    unchanged_value: if True, returns current value of the field
                     when PreparedFieldValue value is requested via 'return_value' method.
                     Used to generate PUT PATCH test datasets
    """

    value: Optional[object] = None
    generated_value: bool = False
    error_messages: Optional[Union[list, dict]] = None
    f_type: Optional["BaseType"] = None

    drop_key: bool = False
    unchanged_value: bool = False

    @dispatch(object)
    def return_value(self, pre_generated_value):
        """
        Return value in final view for fields in POST body tests
        :param pre_generated_value: Pre-generated valid value for set POSTable field value
        """
        if self.generated_value:
            if pre_generated_value is not None:
                return pre_generated_value
            return self.f_type.generate()

        return self.value

    @dispatch(object, object, object)  # pylint: disable=function-redefined
    def return_value(self, dbfiller, current_field_value, changed_field_value):  # noqa: F811
        """
        Return value in final view for fields in PUT, PATCH body tests
        :param dbfiller: Object of class DbFiller. Required to create non-changeable fk fields
        :param current_field_value: Value with which creatable object was created
        :param changed_field_value: Valid value to which we can change original if possible
        """
        if self.generated_value:
            if changed_field_value is not None:
                return changed_field_value
            if isinstance(self.f_type, Enum):
                return self.f_type.generate_new(old_value=current_field_value)
            if isinstance(self.f_type, ForeignKey):
                return dbfiller.generate_new_value_for_unchangeable_fk_field(
                    f_type=self.f_type, current_field_value=current_field_value
                )
            if isinstance(self.f_type, GenericForeignKeyList):
                return dbfiller.generate_new_value_for_generic_foreign_key_list(
                    current_value=current_field_value,
                )
            return self.f_type.generate_new(current_field_value)

        return self.value

    def get_error_data(self):
        """Error data is a list by default but fk fields should be nested"""
        return self.error_messages


class Relation(NamedTuple):
    """Named tuple for relates_on attribute"""

    field: "Field"
    data_class: Type["data_classes.BaseClass"] = None


@attr.dataclass
class BaseType(ABC):
    """
    Base type of field
    Contains common methods and attributes for each types
    """

    # Tuple of class + field name to get related schema or other limitations
    relates_on: Optional[Relation] = None

    _sp_vals_positive: Optional[list] = None
    _sp_vals_negative: Optional[List[Union[object, Type["BaseType"], PreparedFieldValue]]] = None

    is_huge: ClassVar[bool] = False
    error_message_not_be_null: ClassVar[str] = "This field may not be null."
    error_message_required: ClassVar[str] = "This field is required."
    error_message_cannot_be_changed: ClassVar[str] = "This field cannot be changed"
    error_message_invalid_data: ClassVar[str] = ""

    @abstractmethod
    def generate(self, **kwargs):
        """Should generate and return one value for the current child type"""

    def generate_new(self, old_value, **kwargs):
        """Generate new field value that is not equal to old one. For PATCH and PUT"""
        for _ in range(10):
            if (new_value := self.generate(**kwargs)) != old_value:
                return new_value
        # if we were unable to generate new value in 10 attempts than we return old one
        # and print warning
        warnings.warn(RuntimeWarning("Failed to generate new value in 10 attempts. Using old one"))
        return old_value

    def get_positive_values(self):
        """Positive values is:
        - boundary values
        - generated values
        - all enum values (if present)
        """
        if self._sp_vals_positive:
            return [PreparedFieldValue(value, f_type=self) for value in self._sp_vals_positive]
        return [PreparedFieldValue(generated_value=True, f_type=self)]

    def get_negative_values(self):
        """Negative values is:
        - out of boundary values
        - invalid choice of enum values
        - invalid FK values
        - invalid type values (generated)
        """
        negative_values = self._sp_vals_negative.copy() if self._sp_vals_negative else []

        final_negative_values = []
        for negative_value in negative_values:
            if isinstance(negative_value, PreparedFieldValue):
                final_negative_values.append(negative_value)
            else:
                final_negative_values.append(
                    PreparedFieldValue(
                        negative_value,
                        f_type=self,
                        error_messages=[self.error_message_invalid_data],
                    )
                )
        return final_negative_values


class PositiveInt(BaseType):
    """Positive int field type"""

    _min_int64 = 0
    _max_int64 = (2**63) - 1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sp_vals_positive = [self._min_int64, self._max_int64]
        self._sp_vals_negative = [
            3.14,
            gen_string(),
            generate_json_from_schema(json_schema=None),
            PreparedFieldValue(
                self._min_int64 - 1,
                f_type=self,
                error_messages=["Ensure this value is greater than or equal to 0."],
            ),
            PreparedFieldValue(
                self._max_int64 + 1,
                f_type=self,
                error_messages=[f"Ensure this value is less than or equal to {self._max_int64}."],
            ),
        ]
        self.error_message_invalid_data = "A valid integer is required."

    def generate(self, **kwargs):
        return randint(self._min_int64, self._max_int64)


class SmallIntegerID(BaseType):
    """Sort of technical type to represent small integer ID to use as a value for foreign keys"""

    def __init__(self, max_value: int, **kwargs):
        super().__init__(**kwargs)
        self.max_value = max_value

    def generate(self, **kwargs):
        return random.randint(1, self.max_value + 1)


class Boolean(BaseType):
    """Boolean field type"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.error_message_invalid_data = "Must be a valid boolean."
        self._sp_vals_negative = ["Invalid string", 321]

    def generate(self, **kwargs):
        return random.choice([True, False])


class String(BaseType):
    """String field type"""

    def __init__(self, max_length=1024, special_chars=r"!@#$%^&*\/{}[]", **kwargs):
        super().__init__(**kwargs)
        self.max_length = max_length
        self._sp_vals_positive = ["s", special_chars, random_string(max_length)]

        self._sp_vals_negative = [
            generate_json_from_schema(json_schema=None),
            PreparedFieldValue(
                value="some\nstring",
                f_type=self,
                error_messages=["New line symbols are not allowed"],
            ),
            PreparedFieldValue(
                value=random_string(max_length + 1),
                f_type=self,
                error_messages=[f"Ensure this field has no more than {max_length} characters."],
            ),
        ]
        self.error_message_invalid_data = "Not a valid string."

    def generate(self, **kwargs):
        return random_string(randint(1, self.max_length))


class Username(String):
    """Username field type"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sp_vals_negative.append(
            PreparedFieldValue(
                value="string with spaces",
                error_messages=["Space symbols are not allowed"],
            )
        )


class Password(BaseType):
    """
    Password field type
    placeholder - it is expected value for all requests
    """

    def __init__(self, placeholder="******", **kwargs):
        super().__init__(**kwargs)
        self.placeholder = placeholder

    def generate(self, **kwargs):
        return random_string()


class Text(BaseType):
    """Text field type"""

    is_huge = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sp_vals_negative = []
        self.error_message_invalid_data = ""

    def generate(self, **kwargs):
        return random_string(randint(64, 200))


class Email(BaseType):
    """Email field type"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sp_vals_negative = ["invalid string", 321]
        self.error_message_invalid_data = "Enter a valid email address."

    def generate(self, **kwargs):
        return f"{random_string(10)}@{random_string(5).lower()}.com"


class DateTime(BaseType):
    """Datetime field type"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sp_vals_negative = [Json]
        self.error_message_invalid_data = ""

    def generate(self, **kwargs):
        return random_datetime()


class Json(BaseType):
    """Json field type"""

    schema = None
    is_huge = True

    def __init__(self, schema=None, **kwargs):
        self.schema = schema
        super().__init__(**kwargs)
        self._sp_vals_negative = []
        self.error_message_invalid_data = ""

    def generate(self, **kwargs):
        return generate_json_from_schema(json_schema=self.schema)


class Enum(BaseType):
    """Enum field type"""

    enum_values: list

    def __init__(self, enum_values, **kwargs):
        super().__init__(**kwargs)
        self.enum_values = enum_values
        value = random_string()
        while True:
            if value not in self.enum_values:
                break
        self._sp_vals_negative = [
            PreparedFieldValue(
                value,
                f_type=Type[String],
                error_messages=[f'"{value}" is not a valid choice.'],
            )
        ]

    def generate(self, **kwargs):
        return choice(self.enum_values)

    def generate_new(self, old_value, **kwargs):
        """Generate new field value that is not equal to old one. For PATCH and PUT"""
        enum_values_wo_current = self.enum_values.copy()
        if old_value in enum_values_wo_current:
            enum_values_wo_current.remove(old_value)
        try:
            return choice(enum_values_wo_current)
        except IndexError as error:
            raise ValueError("There is no available enum values except old one") from error


class ForeignKey(BaseType):
    """Foreign key field type"""

    def __init__(self, fk_link: Type["data_classes.BaseClass"] = None, **kwargs):
        self.fk_link = fk_link
        super().__init__(**kwargs)
        self._sp_vals_negative = [
            PreparedFieldValue(
                100,
                f_type=self,
                error_messages=['Invalid pk "100" - object does not exist.'],
            ),
            PreparedFieldValue(
                2**63,
                f_type=self,
                error_messages=[f'Invalid pk "{2**63}" - object does not exist.'],
            ),
        ]

    def generate(self, **kwargs):
        """You can't just generate a new FK. This is done inside db_filler"""
        pass  # pylint: disable=unnecessary-pass


class ObjectForeignKey(ForeignKey):
    """Object foreign key field type (e.g. {'id': 2})"""

    def __init__(self, fk_link: Type["data_classes.BaseClass"] = None, **kwargs):
        super().__init__(fk_link=fk_link, **kwargs)
        self._sp_vals_negative = [
            PreparedFieldValue(
                {"id": 1000},
                f_type=self,
                error_messages={"id": ['Invalid pk "1000" - object does not exist.']},
            ),
            PreparedFieldValue(
                {"id": 2**63},
                f_type=self,
                error_messages={"id": [f'Invalid pk "{2**63}" - object does not exist.']},
            ),
        ]


class BackReferenceFK(BaseType):
    """Back reference foreign key field type"""

    fk_link: Optional[Type["data_classes.BaseClass"]] = None

    def __init__(self, fk_link: Type["data_classes.BaseClass"], **kwargs):
        self.fk_link = fk_link
        super().__init__(**kwargs)

    def generate(self, **kwargs):
        return 42


class ForeignKeyM2M(ForeignKey):
    """Foreign key many to many field type"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sp_vals_negative = [
            PreparedFieldValue(
                [{"id": 1000}],
                f_type=self,
                error_messages=[{"id": ['Invalid pk "1000" - object does not exist.']}],
            ),
            PreparedFieldValue(
                [{"id": 2**63}],
                f_type=self,
                error_messages=[{"id": [f'Invalid pk "{2**63}" - object does not exist.']}],
            ),
        ]


class GenericForeignKeyList(BaseType):
    """List with generic foreign keys (special variant of ListOf(Json))"""

    payload: List[dict]

    def generate(self, **kwargs):
        """
        No need to directly generate such a field,
        payload should be set during "relates_on" resolving and requested directly
        """


class ListOf(BaseType):
    """List field type"""

    item_type: BaseType

    def __init__(self, item_type: BaseType, **kwargs):
        self.item_type = item_type
        super().__init__(**kwargs)
        self._sp_vals_negative = [
            PreparedFieldValue(
                [neg.value],
                f_type=neg.f_type,
            )
            for neg in item_type.get_negative_values()
        ]

    def generate(self, **kwargs):
        return [self.item_type.generate(**kwargs)]


class EmptyList(BaseType):
    """Empty list type (for corner cases to ensure empty list is sent)"""

    def generate(self, **kwargs):
        return []


@attr.dataclass
class Field:  # pylint: disable=too-many-instance-attributes
    """Field class based on ADCM API spec"""

    name: str
    f_type: Optional[BaseType] = None
    default_value: Optional[object] = None
    nullable: bool = False
    # Some fields are declared as nullable but with
    # * about field value validation on another logical level
    # such fields should be excluded from autogenerated datasets
    dynamic_nullable: bool = False
    changeable: bool = False
    postable: bool = False
    required: bool = False
    # Some fields are declared as non-required but with
    # * about field value validation on another logical level
    # such fields should be excluded from autogenerated datasets
    custom_required: bool = False


def get_fields(data_class: type, predicate: Callable = None) -> List[Field]:
    """Get fields by data class and filtered by predicate"""

    def dummy_predicate(_):
        return True

    if predicate is None:
        predicate = dummy_predicate
    return [
        value
        for (
            key,
            value,
        ) in data_class.__dict__.items()
        if isinstance(value, Field) and predicate(value)
    ]


def is_password_field(field: Field) -> bool:
    """Predicate for password fields selection"""
    return isinstance(field.f_type, Password)


def is_fk_field(field: Field) -> bool:
    """Predicate for fk fields selection"""
    return isinstance(field.f_type, ForeignKey)


def is_fk_field_only(field):
    """True if field is ForeignKey and not ForeignKeyM2M"""
    return type(field.f_type) is ForeignKey  # pylint: disable=unidiomatic-typecheck


def is_fk_or_back_ref(field: Field) -> bool:
    """Predicate for fk and back reference fields"""
    return isinstance(field.f_type, (ForeignKey, BackReferenceFK))


def is_huge_field(field):
    """Predicate for select only huge fields"""
    return field.f_type.is_huge


def is_list_fields(field):
    """Predicate for select allowed fields for LIST method"""
    return not is_huge_field(field) and not is_fk_or_back_ref(field)


def get_field_name_by_fk_dataclass(data_class: type, fk_data_class: type) -> str:
    """Get field name in data_class that is FK to another data_class"""
    for field in get_fields(data_class, predicate=is_fk_field):
        if field.f_type.fk_link == fk_data_class:
            return field.name
    raise AttributeError(f"No FK field pointing to {fk_data_class} found!")
