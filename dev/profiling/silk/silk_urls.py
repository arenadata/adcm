from django.conf.urls import include
from django.urls import path

from .urls import urlpatterns


urlpatterns += [path("api/silk/", include("silk.urls", namespace="silk"))]
