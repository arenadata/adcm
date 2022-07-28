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

from django.test import Client, TestCase
from django.urls import reverse
from audit.models import (
    AuditLog,
    AuditObject,
    AuditSession,
    AuditLogOperationType,
    AuditObjectType,
    AuditLogOperationResult,
    AuditSessionLoginResult,
)
from rbac.models import User


class TestBase(TestCase):
    def setUp(self) -> None:
        self.user_username = 'user_username'
        self.user_password = 'user_password'
        self.superuser_username = 'superuser_username'
        self.superuser_password = 'superuser_password'

        self.user = User.objects.create_user(
            **{
                'username': self.user_username,
                'password': self.user_password,
                'is_superuser': False,
            }
        )
        self.superuser = User.objects.create_user(
            **{
                'username': self.superuser_username,
                'password': self.superuser_password,
                'is_superuser': True,
            }
        )

        self.client = Client(HTTP_USER_AGENT='Mozilla/5.0')

    def tearDown(self) -> None:
        AuditLog.objects.all().delete()
        AuditObject.objects.all().delete()
        AuditSession.objects.all().delete()

    def _login_as(self, username, password):
        res = self.client.post(
            path=reverse("rbac:token"),
            data={"username": username, "password": password},
            content_type="application/json",
        )
        self.client.defaults["Authorization"] = f"Token {res.data['token']}"

    def _populate_audit_tables(
        self,
        object_type: AuditObjectType = None,
        operation_type: AuditLogOperationType = None,
        operation_result: AuditLogOperationResult = None,
        operation_name: str = None,
        object_name: str = None,
        is_deleted: bool = False,
        user: User = None,
        object_changes: dict = None,
        date: str = None,
        login_result: AuditSessionLoginResult = None,
        login_details: dict = None,
        num: int = 100,
    ):
        user = user or self.superuser
        object_changes = object_changes or {
            "current": {"attr_name": "email", "attr_value": "test@ma.il"},
            "previous": {"attr_name": "email", "attr_value": "new@ma.il"},
        }
        login_details = login_details or {'username': 'test_username'}

        for i in range(num):
            if all([object_type, operation_type, operation_result]):
                ao = AuditObject.objects.create(
                    object_id=i,
                    object_name=object_name or f'obj_name_{i}',
                    object_type=object_type,
                    is_deleted=is_deleted,
                )
                al = AuditLog.objects.create(
                    audit_object=ao,
                    operation_name=operation_name or f'operation_name_{i}',
                    operation_type=operation_type,
                    operation_result=operation_result,
                    user=user,
                    object_changes=object_changes,
                )
                if date:
                    AuditLog.objects.filter(pk=al.pk).update(operation_time=date)
            if login_result:
                AuditSession.objects.create(
                    user=user, login_result=login_result, login_details=login_details
                )


class TestViews(TestBase):
    def test_audit_visibility_regular_user(self):
        self._login_as(self.user_username, self.user_password)
        self._populate_audit_tables(
            object_type=AuditObjectType.Cluster,
            operation_type=AuditLogOperationType.Create,
            operation_result=AuditLogOperationResult.Success,
            is_deleted=False,
            login_result=AuditSessionLoginResult.Success,
            user=self.superuser,
            num=101,
        )
        response = self.client.get(
            path=reverse('audit-operations'), content_type="application/json"
        ).json()
        assert response['count'] == 0
        assert not response['results']

    def test_audit_visibility_superuser(self):
        self._login_as(self.superuser_username, self.superuser_password)
        self._populate_audit_tables(
            object_type=AuditObjectType.Cluster,
            operation_type=AuditLogOperationType.Create,
            operation_result=AuditLogOperationResult.Success,
            is_deleted=False,
            login_result=AuditSessionLoginResult.Success,
            user=self.superuser,
            num=101,
        )
        response = self.client.get(
            path=reverse('audit-operations'), content_type="application/json"
        ).json()
        assert response['count'] == 101
        assert response['results']

    def test_filters(self):
        self._login_as(self.superuser_username, self.superuser_password)
        self._populate_audit_tables(
            object_type=AuditObjectType.Cluster,
            operation_type=AuditLogOperationType.Create,
            operation_result=AuditLogOperationResult.Success,
            is_deleted=False,
            login_result=AuditSessionLoginResult.Success,
            user=self.superuser,
            num=2,
        )
        date = '2000-01-05'
        operation_name = 'test_name'
        object_name = 'test_obj_name'
        self._populate_audit_tables(
            object_type=AuditObjectType.Group,
            operation_type=AuditLogOperationType.Update,
            object_name=object_name,
            operation_result=AuditLogOperationResult.Fail,
            is_deleted=False,
            operation_name=operation_name,
            login_result=AuditSessionLoginResult.WrongPassword,
            user=self.user,
            date=date,
            num=3,
        )

        response = self.client.get(
            path=reverse('audit-operations'), content_type="application/json"
        ).json()
        assert response['count'] == 5

        response = self.client.get(
            path=reverse('audit-operations'),
            data={'object_type': 'cluster'},
            content_type="application/json",
        ).json()
        assert response['count'] == 2

        response = self.client.get(
            path=reverse('audit-operations'),
            data={'object_name': object_name},
            content_type="application/json",
        ).json()
        assert response['count'] == 3

        response = self.client.get(
            path=reverse('audit-operations'),
            data={'operation_type': 'update'},
            content_type="application/json",
        ).json()
        assert response['count'] == 3

        response = self.client.get(
            path=reverse('audit-operations'),
            data={'operation_name': operation_name},
            content_type="application/json",
        ).json()
        assert response['count'] == 3

        response = self.client.get(
            path=reverse('audit-operations'),
            data={'operation_result': 'fail'},
            content_type="application/json",
        ).json()
        assert response['count'] == 3

        response = self.client.get(
            path=reverse('audit-operations'),
            data={'username': self.user_username},
            content_type="application/json",
        ).json()
        assert response['count'] == 3

        response = self.client.get(
            path=reverse('audit-operations'),
            data={'operation_date': date},
            content_type="application/json",
        ).json()
        assert response['count'] == 3
