from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator

from cm.errors import AdcmEx


class RegExValidator(RegexValidator):
    def __init__(self, regex: str, *args, error_code: str, error_msg: str = "", **kwargs):
        super().__init__(regex, *args, **kwargs)
        self.error_code = error_code
        self.error_msg = error_msg

    def __call__(self, value):
        try:
            super().__call__(value)
        except DjangoValidationError as e:
            raise AdcmEx(code=self.error_code, msg=self.error_msg.format(value=value)) from e


ClusterNameRegExValidator = RegExValidator(
    regex=settings.CLUSTER_NAME_PATTERN,
    error_code="WRONG_NAME",
    error_msg="Name `{value}` doesn't meets requirements",
)
