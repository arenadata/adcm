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

from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from audit.alt.core import AuditSignature, Hooks, OperationAuditContext
from audit.alt.hooks import AuditHook
from audit.alt.object_retrievers import ignore_object_search
from audit.models import AuditLogOperationResult, AuditLogOperationType, AuditUser

T = TypeVar("T")
P = ParamSpec("P")


class BackgroundOperationAuditContext(OperationAuditContext):
    def save_on_start(self) -> None:
        self.name = f"{self._default_name} launched"
        self.result = AuditLogOperationResult.SUCCESS
        self.run_pre_call_hooks()
        self.save()
        self.restore_defaults()

    def save_on_finish(self) -> None:
        self.name = f"{self._default_name} completed"
        self.collect().save()
        self.restore_defaults()


class SetBackgroundOperationState(AuditHook):
    def __call__(self):
        self.context.result = AuditLogOperationResult.FAIL if self.exception else AuditLogOperationResult.SUCCESS


class SetSystemUser(AuditHook):
    def __call__(self):
        self.context.user = AuditUser.objects.filter(username="system").first()


class BackgroundOperationAudit:
    def __init__(self, name: str, type_: AuditLogOperationType):
        self._context: BackgroundOperationAuditContext = BackgroundOperationAuditContext(
            signature=AuditSignature(id="Background operation", type=type_),
            default_name=name,
            retrieve_object=ignore_object_search,
            # pre call will be called when creating initial operation record,
            # on collect on creating finishing one
            custom_hooks=Hooks(pre_call=(SetSystemUser,), on_collect=(SetBackgroundOperationState, SetSystemUser)),
        )

    @property
    def context(self) -> BackgroundOperationAuditContext:
        return self._context

    def __call__(self, func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapped(*args, **kwargs) -> T:
            with self:
                return func(*args, **kwargs)

        return wrapped

    def __enter__(self):
        self._context.restore_defaults()
        self._context.save_on_start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._context.attach_exception(exc_val)
        self._context.save_on_finish()


# convenient naming to use as decorator
audit_background_operation = BackgroundOperationAudit
