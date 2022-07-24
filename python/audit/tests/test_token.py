from datetime import datetime

from audit.models import (
    AUDIT_OPERATION_MAP,
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)
from django.urls import reverse
from rest_framework.response import Response

from adcm.tests.base import BaseTestCase


class TestToken(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.audit_operation_create_token = AUDIT_OPERATION_MAP["GetAuthToken"]["POST"]

    def test_create(self):
        res: Response = self.client.post(
            path=reverse("rbac:token"),
            data={
                "username": self.test_user_username,
                "password": self.test_user_password,
            },
        )

        res: Response = self.client.post(
            path=reverse("token"),
            data={
                "username": self.test_user_username,
                "password": self.test_user_password,
            },
        )
