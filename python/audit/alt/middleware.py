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

from django.urls import resolve

from audit.alt.api import (
    AUDITED_HTTP_METHODS,
    APIOperationAuditContext,
    AuditedEndpointConfig,
    AuditEndpointsRegistry,
    get_endpoints_registry,
)
from audit.alt.core import AuditSignature


class AuditMiddleware:
    """
    Audit controller functions that are registered in AuditEndpointsRegistry.

    Since `process_view` is executed previously to actual response handling,
    it will handle pre-request hooks and audit context preparation.

    Sync only (see `skip_audit` and `current_audit_context` usage).
    """

    def __init__(self, get_response):
        self.get_response = get_response

        self.audited_endpoints_registry: AuditEndpointsRegistry = get_endpoints_registry()

        self.skip_audit = False
        self.current_audit_context: APIOperationAuditContext | None = None

    def __call__(self, request):
        self.current_audit_context = None
        self.skip_audit = request.method not in AUDITED_HTTP_METHODS

        response = self.get_response(request)
        if self.skip_audit or self.current_audit_context is None:
            return response

        self.current_audit_context.attach_result(result=response).collect().save()

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):  # noqa: ARG002
        endpoint_config: AuditedEndpointConfig | None = self.audited_endpoints_registry.find_for_view(
            http_method=request.method, view_func=view_func
        )
        if not endpoint_config:
            return

        signature = AuditSignature(id=resolve(request.path).route, type=endpoint_config.operation_type)
        self.current_audit_context = APIOperationAuditContext(
            signature=signature,
            default_name=endpoint_config.operation_name,
            retrieve_object=endpoint_config.retrieve_object_func,
            custom_hooks=endpoint_config.hooks,
        )
        self.current_audit_context.attach_call_arguments(arguments=view_kwargs | {"request": request})
        self.current_audit_context.run_pre_call_hooks()
