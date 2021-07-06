"""Module contains all field types and it special values"""
import warnings
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timedelta
from random import randint, choice
from typing import ClassVar, List, Type, Union, NamedTuple
from multipledispatch import dispatch

import attr

from tests.utils.tools import random_string
from tests.utils.fake_data import generate_json_from_schema, gen_string

# There is no circular import, because the import of the module is not yet completed at the moment,
# and this allows you to resolve the conflict.
from tests.utils import data_classes  # pylint: disable=unused-import,cyclic-import


def random_json():
    """Generating json with random key values"""
    return {"int": randint(1, 100), "str": random_string()}


def random_datetime():
    """Generating datetime"""
    return (datetime.now() + timedelta(randint(-1000, 1000))).strftime("%Y-%m-%dT%H:%M:%SZ")


@attr.dataclass
class PreparedFieldValue:  # pylint: disable=too-few-public-methods,function-redefined
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

    value: object = None
    generated_value: bool = False
    error_messages: Union[list, dict] = None
    f_type: "BaseType" = None

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
            return self.f_type.generate()

        return self.value

    def get_error_data(self):
        """Error data is a list by default but fk fields should be nested"""
        return self.error_messages


class Relation(NamedTuple):
    """Named tuple for relates_on attribute"""

    data_class: Type["data_classes.BaseClass"]
    field: "Field"


@attr.dataclass
class BaseType(ABC):
    """
    Base type of field
    Contains common methods and attributes for each types
    """

    # tuple of class + field name to get related schema or other limitations
    relates_on: Relation = None

    _sp_vals_positive: list = None
    _sp_vals_negative: List[Union[object, Type["BaseType"], PreparedFieldValue]] = None

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
    _max_int64 = (2 ** 63) - 1

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


class String(BaseType):
    """String field type"""

    def __init__(self, max_length=1024, **kwargs):
        super().__init__(**kwargs)
        self.max_length = max_length
        self._sp_vals_positive = ['s', r'!@#$%^&*\/{}[]', random_string(max_length)]

        self._sp_vals_negative = [
            generate_json_from_schema(json_schema=None),
            PreparedFieldValue(
                value='some\nstring',
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


class Text(BaseType):
    """Text field type"""

    is_huge = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sp_vals_negative = []
        self.error_message_invalid_data = ""

    def generate(self, **kwargs):
        return random_string(randint(64, 200))


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

    is_huge = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sp_vals_negative = []
        self.error_message_invalid_data = ""

    def generate(self, **kwargs):
        return generate_json_from_schema(json_schema=kwargs.get("schema", None))


class Enum(BaseType):
    """Enum field type"""

    enum_values: list

    def __init__(self, enum_values, **kwargs):
        super().__init__(**kwargs)
        self.enum_values = enum_values
        while (value := random_string()) in self.enum_values:
            pass
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


class CronLine(String):
    """Cronline field type. Based on String"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.error_message_invalid_data = 'Cron-line has wrong format'
        self._sp_vals_positive = []
        self._sp_vals_negative = [
            '61 * * * *',
            random_string(20),
        ]

    def generate(self, **kwargs):
        past_date = datetime.now() - timedelta(weeks=1, minutes=randint(1, 60))
        return f'{past_date.minute} {past_date.hour} {past_date.day} * *'


class ForeignKey(BaseType):
    """Foreign key field type"""

    fk_link: Type["data_classes.BaseClass"] = None

    def __init__(self, fk_link: Type["data_classes.BaseClass"], **kwargs):
        self.fk_link = fk_link
        super().__init__(**kwargs)
        self._sp_vals_negative = [
            PreparedFieldValue(
                {"id": 100},
                f_type=self,
                error_messages={"id": ["Invalid ID. Object with ID 100 does not exist."]},
            ),
            PreparedFieldValue(
                {"id": 2 ** 63},
                f_type=self,
                error_messages={"id": [f"Invalid ID. Object with ID {2 ** 63} does not exist."]},
            ),
        ]

    def generate(self, **kwargs):
        pass


class BackReferenceFK(BaseType):
    """Back reference foreign key field type"""

    fk_link: Type["data_classes.BaseClass"] = None

    def __init__(self, fk_link: Type["data_classes.BaseClass"], **kwargs):
        self.fk_link = fk_link
        super().__init__(**kwargs)

    def generate(self, **kwargs):
        return {"id": 42}


class ForeignKeyM2M(ForeignKey):
    """Foreign key many to many field type"""


@attr.dataclass
class Field:  # pylint: disable=too-few-public-methods
    """Field class based on ADSS spec"""

    name: str
    f_type: BaseType = None
    default_value: object = None
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
        for (key, value) in data_class.__dict__.items()
        if isinstance(value, Field) and predicate(value)
    ]


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
