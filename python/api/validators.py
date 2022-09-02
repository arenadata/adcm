import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator

from cm.errors import AdcmEx

CLUSTER_NAME_PATTERN = re.compile(
    r"^[a-zA-Z]"  # starts with latin letter (upper/lower case)
    r"[a-zA-Z0-9\-\. ]*?"  # latin letters (upper/lower case), digits, hyphens, dots, whitespaces
    r"[a-zA-Z0-9]$"  # ends with latin letter (upper/lower case) or digit
)  # as a result of this pattern min_length = 2


class ClusterNameRegExValidator(RegexValidator):
    def __call__(self, value):
        try:
            super().__call__(self, value)
        except DjangoValidationError as e:
            raise AdcmEx(
                code="CLUSTER_CONFLICT", msg=f"Name `{value}` doesn't meet requirements"
            ) from e
