"""Common tools and constants"""
# pylint: disable=too-few-public-methods
import allure


class Layer:
    """
    Decorators of allure layers
    Example:

        @Layer.UI
        def test_ui():
            pass


        @Layer.API
        def test_api():
            pass
    """

    UI = allure.label('layer', 'UI')
    API = allure.label('layer', 'API')
    Unit = allure.label('layer', 'Unit')
