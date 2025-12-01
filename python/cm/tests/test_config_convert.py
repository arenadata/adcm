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

from typing import NamedTuple
from unittest import TestCase

from cm.config.convert import convert_adcm_meta_to_attr, convert_attr_to_adcm_meta

ACTIVE = "isActive"
SYNCHRONIZED = "isSynchronized"


class Case(NamedTuple):
    name: str
    meta: dict
    attr: dict


CASES = [
    Case(name="Empty", meta={}, attr={}),
    Case(
        name="Only active multiple groups",
        meta={
            "/a": {ACTIVE: True},
            "/b/c": {ACTIVE: False},
            "/a/v": {ACTIVE: True},
        },
        attr={"a": {"active": True}, "b/c": {"active": False}, "a/v": {"active": True}},
    ),
    Case(
        name="One level group with sync and active",
        meta={
            "/a": {ACTIVE: True, SYNCHRONIZED: True},
            "/a/b1": {SYNCHRONIZED: True},
            "/a/b2": {SYNCHRONIZED: False},
            "/c": {SYNCHRONIZED: False},
            "/g/v1": {SYNCHRONIZED: False},
            "/d": {SYNCHRONIZED: True},
        },
        attr={
            "a": {"active": True},
            "group_keys": {
                "a": {
                    "fields": {"b1": False, "b2": True},
                    "value": False,
                },
                "c": True,
                "g": {"fields": {"v1": True}, "value": None},
                "d": False,
            },
        },
    ),
    Case(
        name="Three level group with sync",
        meta={
            "/a": {ACTIVE: True, SYNCHRONIZED: True},
            "/a/b1": {SYNCHRONIZED: True},
            "/a/bg/act": {ACTIVE: False, SYNCHRONIZED: False},
            "/a/bg/act/v1": {SYNCHRONIZED: False},
            "/a/bg/v1": {SYNCHRONIZED: True},
            "/a/b2": {SYNCHRONIZED: False},
            "/c": {SYNCHRONIZED: False},
            "/d": {SYNCHRONIZED: True},
        },
        attr={
            "a": {"active": True},
            "a/bg/act": {"active": False},
            "group_keys": {
                "a": {
                    "fields": {
                        "b1": False,
                        "b2": True,
                        "bg": {
                            "fields": {"v1": False, "act": {"fields": {"v1": True}, "value": True}},
                            "value": None,
                        },
                    },
                    "value": False,
                },
                "c": True,
                "d": False,
            },
        },
    ),
    Case(
        name="Child before group",
        meta={
            "/a/v": {SYNCHRONIZED: True},
            "/a/g/c": {SYNCHRONIZED: False},
            "/a": {ACTIVE: False, SYNCHRONIZED: False},
        },
        attr={
            "a": {"active": False},
            "group_keys": {
                "a": {
                    "fields": {
                        "v": False,
                        "g": {"fields": {"c": True}, "value": None},
                    },
                    "value": True,
                }
            },
        },
    ),
]


class TestMetaAttrConversion(TestCase):
    maxDiff = None

    def test_convert_meta_to_attr(self):
        convert = convert_adcm_meta_to_attr

        for case in CASES:
            with self.subTest(case.name):
                result = convert(case.meta)
                self.assertDictEqual(result, case.attr)

    def test_convert_attr_to_meta(self):
        convert = convert_attr_to_adcm_meta

        for case in CASES:
            with self.subTest(case.name):
                result = convert(case.attr)
                self.assertDictEqual(result, case.meta)
