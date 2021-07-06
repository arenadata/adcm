"""Set package-wise test properties"""
import allure
from tests.utils.common import Layer

pytestmark = [Layer.API, allure.parent_suite("Functional")]
