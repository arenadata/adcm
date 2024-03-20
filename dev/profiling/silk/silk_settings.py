from .settings import *

INSTALLED_APPS.append("silk")

MIDDLEWARE.insert(0, "silk.middleware.SilkyMiddleware")

DEBUG = True
SILKY_PYTHON_PROFILER = True

ROOT_URLCONF = "adcm.silk_urls"
