from debug_toolbar.toolbar import debug_toolbar_urls
from .urls import urlpatterns

urlpatterns += debug_toolbar_urls()
