import re

from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator

from cm.errors import AdcmEx


class HostUniqueValidator(UniqueValidator):
    def __call__(self, value, serializer_field):
        try:
            super().__call__(value, serializer_field)
        except ValidationError as e:
            raise AdcmEx("HOST_CONFLICT", "duplicate host") from e


class RegexValidator:
    def __init__(self, regex: str, code: str, msg: str):
        self._regex = re.compile(regex)
        self._code = code
        self._msg = msg

    def __call__(self, value: str):
        if not re.fullmatch(pattern=self._regex, string=value):
            raise AdcmEx(self._code, self._msg)
