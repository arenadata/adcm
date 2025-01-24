import mimetypes
from .settings import *


def return_true(*args, **kwargs) -> bool:
    return True


DEBUG = True

INSTALLED_APPS.append("debug_toolbar")

MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

INTERNAL_IPS = ["127.0.0.1"]

DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": "adcm.ddt_settings.return_true",
}

ROOT_URLCONF = "adcm.ddt_urls"

mimetypes.add_type("application/javascript", ".js", True)
