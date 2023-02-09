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
Settings for ADWP RBAC are all namespaced in the ADWP_RBAC setting.
For example your project's `settings.py` file might look like this:

ADWP_RBAC = {
    'ROLE_SPEC': 'role_spec.yaml',
    'ROLE_SCHEMA': 'role_schema.yaml',
}

This module provides the `api_setting` object, that is used to access
settings, checking for user settings first, then falling
back to the defaults.
"""

import os

from django.conf import settings
from django.test.signals import setting_changed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


DEFAULTS = {
    # File with role specification
    "ROLE_SPEC": os.path.join(BASE_DIR, "upgrade", "role_spec.yaml"),
    # Schema for role specification file
    "ROLE_SCHEMA": os.path.join(BASE_DIR, "upgrade", "role_schema.yaml"),
}


class APISettings:
    """
    A settings object, that allows API settings to be accessed as properties.
    For example:

        from rbac.settings import api_settings
        print(api_settings.ROLE_SCHEMA)

    """

    def __init__(self, user_settings=None, defaults=None):
        self.defaults = defaults or DEFAULTS
        self._cached_attrs = set()
        if user_settings:
            self._user_settings = user_settings

    @property
    def user_settings(self):
        if not hasattr(self, "_user_settings"):
            self._user_settings = getattr(settings, "ADWP_RBAC", {})
        return self._user_settings

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError(f"Invalid API setting: '{attr}'")

        try:
            # Check if present in user settings
            val = self.user_settings[attr]
        except KeyError:
            # Fall back to defaults
            val = self.defaults[attr]

        # Cache the result
        self._cached_attrs.add(attr)
        setattr(self, attr, val)
        return val

    def reload(self):
        for attr in self._cached_attrs:
            delattr(self, attr)
        self._cached_attrs.clear()
        if hasattr(self, "_user_settings"):
            delattr(self, "_user_settings")


api_settings = APISettings(None, DEFAULTS)


def reload_api_settings(*args, **kwargs):  # pylint: disable=unused-argument
    setting = kwargs["setting"]
    if setting == "ADWP_RBAC":
        api_settings.reload()


setting_changed.connect(reload_api_settings)
