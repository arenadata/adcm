import re

from rest_framework.serializers import ValidationError

CLUSTER_NAME_PATTERN = re.compile(
    r"^[a-zA-Z]"  # starts with latin letter (upper/lower case)
    r"[a-zA-Z0-9\-\. ]*?"  # latin letters (upper/lower case), digits, hyphens, dots, whitespaces
    r"[a-zA-Z0-9]$"  # ends with latin letter (upper/lower case) or digit
)  # as a result of this pattern min_length = 2


class CharFieldMatchValidator:
    def __init__(self, regexp: re.Pattern):
        self.regexp = regexp

    def __call__(self, value):
        if not self.regexp.match(value):
            raise ValidationError(f"`{value}` does not match `{self.regexp.pattern}` pattern")
