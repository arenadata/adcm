# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.urls import path
from rest_framework.routers import DefaultRouter

from api.stack.root import StackRoot
from api.stack.views import (
    ADCMPrototypeViewSet,
    BundleViewSet,
    ClusterPrototypeViewSet,
    ComponentPrototypeViewSet,
    HostPrototypeViewSet,
    LoadBundleView,
    ProtoActionViewSet,
    PrototypeViewSet,
    ProviderPrototypeViewSet,
    ServicePrototypeViewSet,
    UploadBundleView,
    load_servicemap_view,
)

router = DefaultRouter()
router.register("bundle", BundleViewSet)
router.register("prototype", PrototypeViewSet)
router.register("action", ProtoActionViewSet)
router.register("service", ServicePrototypeViewSet, basename="service-prototype")
router.register("component", ComponentPrototypeViewSet, basename="component-prototype")
router.register("provider", ProviderPrototypeViewSet, basename="provider-prototype")
router.register("host", HostPrototypeViewSet, basename="host-prototype")
router.register("cluster", ClusterPrototypeViewSet, basename="cluster-prototype")
router.register("adcm", ADCMPrototypeViewSet, basename="adcm-prototype")


urlpatterns = [
    path("", StackRoot.as_view(), name="stack"),
    path("upload/", UploadBundleView.as_view({"post": "create"}), name="upload-bundle"),
    path("load/", LoadBundleView.as_view({"post": "create"}), name="load-bundle"),
    path("load/servicemap/", load_servicemap_view, name="load-servicemap"),
    path(
        "bundle/<int:bundle_pk>/update/",
        BundleViewSet.as_view({"put": "update_bundle"}),
        name="bundle-update",
    ),
    path(
        "bundle/<int:bundle_pk>/license/accept/",
        BundleViewSet.as_view({"put": "accept_license"}),
        name="accept-license",
    ),
    path(
        "prototype/<int:prototype_pk>/license/accept/",
        PrototypeViewSet.as_view({"put": "accept_license"}),
        name="accept-license",
    ),
    *router.urls,  # for correct work of root view router urls must be at bottom of urlpatterns
]
