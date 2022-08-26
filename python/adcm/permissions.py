from rest_framework.permissions import DjangoModelPermissions, DjangoObjectPermissions

from audit.utils import audit


class DjangoObjectPermissionsAudit(DjangoObjectPermissions):
    @audit
    def has_permission(self, request, view):
        return super().has_permission(request, view)


class DjangoModelPermissionsAudit(DjangoModelPermissions):
    @audit
    def has_permission(self, request, view):
        return super().has_permission(request, view)
