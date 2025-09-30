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

from operator import attrgetter
from typing import Any, Iterable, TypeVar
from unittest import TestCase

from core import result as r
from core.config import spec
from core.config._names import level_names_to_full_name
from core.config._types import ParameterFullName, ParameterLevelName
from core.config._validate import PatternValidator, VariantValidator, Violation, Violations

READ_ONLY_STATUS = "dontedit"


T = TypeVar("T")


def name_id(*names: str) -> spec.p.Identifier:
    *_, own = names
    return spec.p.Identifier(name=own, full=level_names_to_full_name(names))


class ConstantVariantResolver(VariantValidator):
    def __init__(self, allowed: Iterable[str]) -> None:
        self.ret = set(allowed)

    def is_value_allowed(self, value: Any, parameter: spec.p.VariantParameter) -> bool:
        _ = parameter
        return value in self.ret


class ConstantPatternValidator(PatternValidator):
    def __init__(self, match: bool) -> None:
        self.ret = match

    def is_match(self, value: str, pattern: str) -> bool:
        _ = value, pattern
        return self.ret


class ConfigTestCase(TestCase):
    def get_name_and_full_name(self, *names: str) -> tuple[ParameterLevelName, ParameterFullName]:
        *_, own_name = names

        return own_name, level_names_to_full_name(names)

    def expect_success(self, result: r.Success[T] | r.Fail) -> r.Success[T]:
        self.assertIsInstance(result, r.Success)

        return result  # pyright: ignore [reportReturnType]

    def expect_fail(self, result: r.Success | r.Fail[T]) -> r.Fail[T]:
        self.assertIsInstance(result, r.Fail)

        return result  # pyright: ignore [reportReturnType]

    def expect_exactly_one_violation(self, result: r.Success | r.Fail[Violations]) -> Violation:
        fail = self.expect_fail(result)
        self.assertEqual(
            len(fail.value), 1, msg=f"Unexpected violations: {'; '.join(map(attrgetter('message'), fail.value))}"
        )
        return fail.value[0]

    def expect_exactly_one_violation_for(
        self,
        result: r.Success | r.Fail[Violations],
        param_is: spec.p.SimpleParameter,
        check_is: str,
        reason_contains: str,
    ) -> Violation:
        violation = self.expect_exactly_one_violation(result=result)

        self.assertEqual(violation.parameter, param_is.identifier.full)
        self.assertEqual(violation.check, check_is)
        self.assertIn(reason_contains, violation.reason)

        return violation
