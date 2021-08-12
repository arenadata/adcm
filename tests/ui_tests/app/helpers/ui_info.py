import allure

from enum import Enum
from typing import Callable, TypeVar, Union

T = TypeVar('T')


class UIComparator(Enum):
    EXACT = 'equal to'
    CONTAINS = 'in'
    EMPTY = 'is empty'


class UIField:

    allure_name: str
    comparator: UIComparator
    value: T
    compare_to: Callable[[T], bool]

    def __init__(
        self,
        allure_name: str,
        comparator: UIComparator = UIComparator.EXACT,
        default_value: T = None,
    ):
        self.allure_name = allure_name
        self.comparator = comparator
        self.value = default_value
        self.compare_to = self.get_comparator_func()

    def __set__(self, instance, value):
        self.value = value

    def get_comparator_func(self) -> Union[Callable[[T], bool], Callable[[], bool]]:
        if self.comparator == UIComparator.EXACT:
            return self.__eq__
        if self.comparator == UIComparator.CONTAINS:
            return self.__contains__
        if self.comparator == UIComparator.EMPTY:
            return self.is_empty
        raise KeyError(
            f'Comparator func for {self.comparator} is not configured in {self.__class__}'
        )

    def is_empty(self):
        return self.value == '' or self.value is None

    def is_not_empty(self):
        return self.value != '' and self.value is not None

    def __eq__(self, other):
        return self.value == other

    def __contains__(self, item):
        return item in self.value


class UIEntityInfo:
    def __init_subclass__(cls, **kwargs):
        ui_fields = [
            attr_name
            for attr_name, attr_class in cls.__dict__.items()
            if isinstance(attr_class, UIField)
        ]

        def init(self, **instance_argument):
            for field in ui_fields:
                if field not in instance_argument and not getattr(self, field):
                    raise AttributeError(f'Attribute "{field}" not provided in __init__ arguments')
                setattr(self, field, instance_argument[field])

        cls.__init__ = init

    @allure.step('Compare with expected values')
    def compare(
        self, expected_values: dict, expected_empty: tuple = (), expected_not_empty: tuple = ()
    ):
        for key, expected_value in expected_values.items():
            field: UIField = getattr(self, key)
            assert field.compare_to(
                expected_value
            ), f'{field.allure_name} should be "{expected_value}", not "{field.value}"'
        for key in expected_empty:
            field: UIField = getattr(self, key)
            assert field.is_empty(), f'{field.allure_name} should be empty'
        for key in expected_not_empty:
            field: UIField = getattr(self, key)
            assert field.is_not_empty(), f'{field.allure_name} should not be empty'


class PopupTaskInfo(UIEntityInfo):
    action_name = UIField('Task action name in popup')
    status = UIField('Job status from popup')
