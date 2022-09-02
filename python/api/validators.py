import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator

from cm.errors import AdcmEx

CLUSTER_NAME_PATTERN = re.compile(
    r"^[a-zA-Z]"  # starts with latin letter (upper/lower case)
    r"[a-zA-Z0-9\-\. ]*?"  # latin letters (upper/lower case), digits, hyphens, dots, whitespaces
    r"[a-zA-Z0-9]$"  # ends with latin letter (upper/lower case) or digit
)  # as a result of this pattern min_length = 2


class RegExValidator(RegexValidator):
    def __init__(
        self, regex: str | re.Pattern, error_code: str, error_msg: str = "", *args, **kwargs
    ):
        super().__init__(regex, *args, **kwargs)
        self.error_code = error_code
        self.error_msg = error_msg

    def __call__(self, value):
        try:
            super().__call__(self, value)
        except DjangoValidationError as e:
            raise AdcmEx(code=self.error_code, msg=self.error_msg.format(value=value)) from e


ClusterNameRegExValidator = RegExValidator(
    regex=CLUSTER_NAME_PATTERN,
    error_code="CLUSTER_CONFLICT",
    error_msg="Name `{value}` doesn't meets requirements",
)
