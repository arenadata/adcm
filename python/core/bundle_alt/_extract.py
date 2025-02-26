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
Dictionary data converter.

Main goal of this module is to extract data from "source" dict (possibly nested) to another dict
that may be used as is or passed to an object's constructor (see `to` function for more info).

IMPORTANT:

This module was originally designed only for Bundle DSL objects -> Bundle Definition objects convertion.
If you want to use it anywhere else, check out assumptions that makes this one work.

---

Usage Assumptions.

1. Basic Python objects are used: dicts, lists, str, float, etc.
2. Absense of value in dict is the same as absense of key.
3. Neither type analisys, nor magic is performed, all mutations must be declared.
   Thou there are some conveniences for `extract` function.

Basics.

1. "Step" is a function that takes "Result" (a.k.a. previous result, input)
   and "Context" (a.k.a. extraction context, evaluation context).
2. Steps are ususally chained with `compose` function that will evaluate all given specs sequentialy,
   returning value from the last evaluated step,
   unless one of them returns `None` value (exactly `None`, not falsy),
   then evaluation is over and `None` is returned.
3. Central function is `extract`.
   It takes `dict` with mapping of "target" dictionary and returns "Step"
   that will process input dictionary based on given mapping.
   Always returns `dict`, thou it may be empty.
   Some sugar goes with this function, allowing to skip verbose constructions
   wherever it wasn't too tricky to implement.
4. "Context" is arbitrary dictionary that may be used in all following steps.
   It has no special restrictions at current state of development,
   yet try to avoid changing it or depending too much on it.
5. There are a bunch of usefull steps already defined in this module,
   but feel free to add your own: interface is simple, just remember that arguments are positional.

Notes on `extract` Syntax.

Each key is "target dictionary" key, value is Step.

When value isn't callable, it's considered list/tuple of arguments to `compose` function:
`{"x": (get("nested"), get("something"))}` is the same as `{"x": compose(get("nested"), get("something"))}`.

Special key "." allows you to "copy" values directly from source dict to target dict:
`{".": ("name", "field")}` is the same as `{"name": get("name"), "field": get("field")}`.
"""

from functools import partial
from typing import Any, Callable, Iterable, TypeAlias

# Basics

_Result: TypeAlias = Any
_Context: TypeAlias = dict

Step: TypeAlias = Callable[[_Result, _Context], Any]


def compose(*steps: Step) -> Step:
    def step(result, context):
        value = result

        for step in steps:
            value = step(value, context)
            if value is None:
                break

        return value

    return step


def extract(mapping: dict) -> Step:
    return partial(_extract_from_value, extraction_rules=mapping)


# Extractors


def const(x) -> Step:
    """Return argument as result, ignoring everything"""
    return lambda _r, _c: x


def get(key: str) -> Step:
    """Get `key` from previous result in a safe way"""
    return lambda r, _: r.get(key)


def from_context(key: str) -> Step:
    """Get `key` from context (`c`) raising `KeyError` if key is missing"""
    return lambda _, c: c[key]


# Converters


def with_defaults(x: dict) -> Step:
    """Use previous results to override / fill given defaults"""
    return lambda r, _: x | r


def cast(x) -> Step:
    """Cast previous result (`r`) to `x` directly: `x(r)`"""
    return lambda r, _: x(r)


def to(x) -> Step:
    """Unpack previous result (`r`) to `x`: `x(**r)`"""
    return lambda r, _: x(**r)


# Composition


def each(x) -> Step:
    """
    Apply given step to all entries in given result (assuming it's list/tuple-like)
    returning list of evaluated values EXCLUDING `None`s
    """
    return lambda r, c: list(filter(lambda e: e is not None, (x(i, c) for i in r)))


def either(main: Step, alt: Step) -> Step:
    """If `main` step evaluates to `None`, returns `alt` step result"""
    return partial(_either, main=main, alt=alt)


# Predicates / Flow Control


def when(x) -> Step:
    """Return `None` (break extraction flow) if `x` evaluates to 'falsy'"""
    return lambda r, c: r if x(r, c) else None


def is_set(key: str) -> Step:
    """Return `bool` wether non-None value can be retrieved from previous result"""
    return lambda r, _: r.get(key) is not None


def any_true(*predicates) -> Step:
    """Return `bool` wether any of given predicates evaluates to `True` based on current result and context"""
    return lambda r, c: any(predicate(r, c) is True for predicate in predicates)


# Steps


def _either(result, context, main, alt):
    primary = main(result, context)
    if primary is not None:
        return primary

    return alt(result, context)


def _extract_from_value(result: dict, context: dict, *, extraction_rules: dict) -> dict:
    out = {}

    for target_key, retrieve in __normalize_rules(extraction_rules):
        value = retrieve(result, context)

        if value is not None:
            out[target_key] = value

    return out


def __normalize_rules(extraction_rules: dict) -> Iterable[tuple[str, Step]]:
    for key, value in extraction_rules.items():
        if key == ".":
            for subkey in value:
                yield subkey, get(subkey)

        elif callable(value):
            yield key, value

        elif isinstance(value, (tuple, list)):
            yield key, compose(*value)
        else:
            raise TypeError(f"Can't convert {key=} {value=} to steps")
