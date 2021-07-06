"""Job lifecycle tests"""
import allure

from tests.utils.common import Layer

pytest_plugins = ["tests.functional.utils.fixtures"]
pytestmark = [Layer.API, allure.parent_suite("Functional"), allure.suite("Job Life Cycle tests")]
