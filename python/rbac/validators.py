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

from cm.errors import raise_adcm_ex
from cm.models import ADCM, ConfigLog
from django.contrib.auth.password_validation import (
    CommonPasswordValidator,
    NumericPasswordValidator,
)
from django.core.exceptions import ValidationError


class ADCMLengthPasswordValidator:
    def __init__(self):
        config_log = None
        self.min_password_length = None
        self.max_password_length = None

        adcm = ADCM.objects.first()
        if adcm:
            config_log = ConfigLog.objects.filter(obj_ref=adcm.config).last()

        if config_log and config_log.config.get("auth_policy"):
            self.min_password_length = config_log.config["auth_policy"]["min_password_length"]
            self.max_password_length = config_log.config["auth_policy"]["max_password_length"]

    def validate(self, password: str, user: None = None) -> None:  # pylint: disable=unused-argument
        if not all((self.min_password_length, self.max_password_length)):
            return

        if len(password) < self.min_password_length:
            raise_adcm_ex(code="USER_PASSWORD_TOO_SHORT_ERROR")

        if len(password) > self.max_password_length:
            raise_adcm_ex(code="USER_PASSWORD_TOO_LONG_ERROR")

    def get_help_text(self):
        return (
            f"Your password can’t be shorter than {self.min_password_length} or longer than {self.max_password_length}."
        )


class ADCMCommonPasswordValidator(CommonPasswordValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password=password, user=user)
        except ValidationError:
            raise_adcm_ex(code="USER_PASSWORD_TOO_COMMON_ERROR")


class ADCMNumericPasswordValidator(NumericPasswordValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password=password, user=user)
        except ValidationError:
            raise_adcm_ex(code="USER_PASSWORD_ENTIRELY_NUMERIC_ERROR")
