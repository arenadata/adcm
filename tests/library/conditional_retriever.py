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

"""
Retrieve data in more than one way in cases when source is unstable
(e.g. data source is at different layers for the same info)
"""
import sys
import traceback
from collections.abc import Callable, Collection
from typing import Any, NamedTuple, TypeVar

import allure

_Result = TypeVar("_Result")


class DataSource(NamedTuple):
    """Wrapper for a function to be called to get the data"""

    getter: Callable
    args: Collection[Any] = ()
    kwargs: dict[str, Any] | None = None

    @property
    def name(self):
        """Get "source" name alongside with the args kwargs (AS IS)"""
        return f'{getattr(self.getter, "__name__", repr(self.getter))} with {self.args=}, {self.kwargs=}'

    def get(self) -> _Result:
        """Call `getter` with args and kwargs"""
        kwargs = self.kwargs or {}
        return self.getter(*self.args, **kwargs)


# to auto-register silencers look into `__init_subclass__`,
# but for now I don't see another silencer than this one
class _ExceptionSilencer:
    __slots__ = ("_type", "_failures")

    _failures: list[tuple[str, str]]

    @property
    def failures(self) -> tuple[tuple[str, str], ...]:
        """Get failures as tuple with items like (name, traceback)"""
        return tuple(self._failures)

    def __init__(self, ex_type: type[Exception]):
        self._type = ex_type
        self._failures = []

    def get(self, source: DataSource) -> tuple[_Result, bool]:
        """Get value and success flag"""
        try:
            return source.get(), True
        except self._type:
            self._failures.append((source.name, traceback.format_exception(*sys.exc_info())))
            return None, False


class FromOneOf:
    """
    Get value from one of the given sources
    and ignore errors that may be raised during fetching the data.

    Try to use it only in cases, when fetching some data/values from UI/API for similar cases
    can't be encapsulated easily and might need unclean workaround.

    e.g.
    there's a row in UI table fields of which may change rarely,
    so to keep Page API clean, you might use `FromOneOf`
    instead of providing yet another conditional flag with extra `if` in method's body.
    """

    _sources: tuple[DataSource, ...]
    _silencer: _ExceptionSilencer

    def __init__(self, data_sources: Collection[DataSource], ignore=Exception):
        if len(data_sources) < 2:
            raise ValueError("There should be at least 2 data sources")
        self._sources = tuple(data_sources)
        self._check_ignore_value_is_correct(ignore)
        self._silencer = _ExceptionSilencer(ignore)

    def __call__(self) -> _Result:
        for source in self._sources:
            result, success = self._silencer.get(source)
            if success:
                return result
        with allure.step("Attach failures"):
            for source_name, failure in self._silencer.failures:
                allure.attach(failure, name=f"Failure from source: {source_name}")
        raise AssertionError("None of the sources returned valuable result")

    def _check_ignore_value_is_correct(self, ignore):
        if isinstance(ignore, type) and issubclass(ignore, BaseException):
            return
        if isinstance(ignore, tuple) and all(issubclass(i, BaseException) for i in ignore):
            return
        raise ValueError(
            "Sorry, but only Exceptions can be ignored with `FromOneOf`.\nFeel free to create your own Silencer.",
        )
