"""
Assume step implementation for allure
"""
from contextlib import suppress
from functools import wraps

import allure
from _pytest.outcomes import Skipped


# pylint: disable=no-else-return
def assume_step(title, exception=None):
    """
    Allows you to suppress exception within the Allure steps.
    Depending on the type of allowed exception, step will receive different statuses -
    - Skipped if suppress Skipped (from pytest.skip())
    - Failed if suppress AssertionError
    - Broken if other

    :param title: same as allure.step() title
    :param exception: allowed exception

    Examples:

    with assume_step('Skipped step'):
        pytest.skip()
    with assume_step('Failed step', exception=AssertionError):
        raise AssertionError("This assert don't fail test")
    with assume_step('Broken step', exception=ValueError):
        raise ValueError("This is expected exception")

    """
    if callable(title):
        return AssumeStepContext(title.__name__, exception)(title)
    else:
        return AssumeStepContext(title, exception)


class AssumeStepContext:
    """
    Step context class
    """

    def __init__(self, title, exception=None):
        self.title = title
        self.exceptions = (Skipped, exception) if exception else Skipped
        self.allure_cm = allure.step(title)
        self.suppress = suppress(self.exceptions)

    def __call__(self, func):
        @wraps(func)
        def decorator(*args, **kwargs):
            with self.suppress:
                return allure.step(self.title)(func)(*args, **kwargs)

        return decorator

    def __enter__(self):
        return self.allure_cm.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.allure_cm.__exit__(exc_type, exc_val, exc_tb)
        return self.suppress.__exit__(exc_type, exc_val, exc_tb)
