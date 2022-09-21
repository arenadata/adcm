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


class StartMidEndValidator:
    """
    start, mid, end - strings with allowed on corresponding position characters
    """

    def __init__(self, start: str, mid: str, end: str, err_code: str, err_msg: str):
        self._start = start
        self._mid_re = re.compile(f"[{re.escape(mid)}]+")
        self._end = end
        self._err_code = err_code
        self._err_msg = err_msg

    def __call__(self, value: str):
        if len(value) < 2:
            raise AdcmEx(code=self._err_code, msg="Min length is 2")

        errors = ""
        if value[0] not in self._start:
            errors += value[0]
        if len(value) >= 3:
            errors += self._mid_re.sub("", value[1:-1])
        if value[-1] not in self._end:
            errors += value[-1]

        if errors:
            raise AdcmEx(code=self._err_code, msg=self._err_msg.format(errors=errors))
