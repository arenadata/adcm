from rest_framework.permissions import DjangoObjectPermissions
from audit.utils import audit


class DjangoObjectPermissionsAudit(DjangoObjectPermissions):
    @audit
    def has_permission(self, request, view):
        return super().has_permission(request, view)
