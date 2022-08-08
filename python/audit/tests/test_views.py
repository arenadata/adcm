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

from copy import deepcopy

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

        self.default_auditobject = {
            'object_id': 0,
            'object_name': 'test_object_name',
            'object_type': AuditObjectType.Cluster,
            'is_deleted': False,
        }
        self.default_auditlog = {
            'operation_name': 'test_operation_name',
            'operation_type': AuditLogOperationType.Create,
            'operation_result': AuditLogOperationResult.Success,
            'object_changes': {'test': {'object': 'changes'}},
        }
        self.default_auditsession = {
            'login_result': AuditSessionLoginResult.Success,
            'login_details': {'test': {'login': 'details'}},
        }

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
        self.tearDown()  # post on login endpoint creates new audit record
        self.client.defaults["Authorization"] = f"Token {res.data['token']}"

    def _populate_audit_tables(
        self,
        auditlog_kwargs: dict = None,
        auditobject_kwargs: dict = None,
        auditsession_kwargs: dict = None,
        num: int = 100,
    ):
        ret = {
            'audit_objects': [],
            'audit_operations': [],
            'audit_logins': [],
        }

        auditobject_kwargs = auditobject_kwargs or deepcopy(self.default_auditobject)
        auditlog_kwargs = auditlog_kwargs or deepcopy(self.default_auditlog)
        auditsession_kwargs = auditsession_kwargs or deepcopy(self.default_auditsession)

        for i in range(num):
            ao = AuditObject.objects.create(**auditobject_kwargs)
            ret['audit_objects'].append(ao)

            if 'audit_object' not in auditlog_kwargs:
                auditlog_kwargs.update({'audit_object': ao})
            if 'user' not in auditlog_kwargs:
                auditlog_kwargs.update({'user': self.superuser})
            operation_time = auditlog_kwargs.pop('operation_time', None)
            al = AuditLog.objects.create(**auditlog_kwargs)
            if operation_time is not None:
                al.operation_time = operation_time
                al.save()  # bypass auto_now_add=True
            ret['audit_operations'].append(al)

            if 'user' not in auditsession_kwargs:
                auditsession_kwargs.update({'user': self.superuser})
            login_time = auditsession_kwargs.pop('login_time', None)
            as_ = AuditSession.objects.create(**auditsession_kwargs)
            if login_time is not None:
                as_.login_time = login_time
                as_.save()  # bypass auto_now_add=True
            ret['audit_logins'].append(as_)
        return ret


class TestViews(TestBase):
    def test_audit_visibility_regular_user(self):
        self._login_as(self.user_username, self.user_password)
        audit_entities = self._populate_audit_tables(num=3)
        response = self.client.get(
            path=reverse('audit:audit-operations-list'), content_type="application/json"
        )
        assert response.status_code == 403
        assert 'results' not in response.json()

        response = self.client.get(
            path=reverse(
                'audit:audit-operations-detail', args=(audit_entities['audit_operations'][0].pk,)
            ),
            content_type="application/json",
        )
        assert response.status_code == 403
        assert 'results' not in response.json()

        response = self.client.get(
            path=reverse('audit:audit-logins-list'), content_type="application/json"
        )
        assert response.status_code == 403
        assert 'results' not in response.json()

        response = self.client.get(
            path=reverse('audit:audit-logins-detail', args=(audit_entities['audit_logins'][0].pk,)),
            content_type="application/json",
        )
        assert response.status_code == 403
        assert 'results' not in response.json()

    def test_audit_visibility_superuser(self):
        self._login_as(self.superuser_username, self.superuser_password)
        num_entities = 5
        audit_entities = self._populate_audit_tables(num=num_entities)
        response = self.client.get(
            path=reverse('audit:audit-operations-list'), content_type="application/json"
        ).json()
        assert response['count'] == num_entities
        assert response['results']
        for item in response['results']:
            assert all(
                [item[field] == self.default_auditlog[field] for field in self.default_auditlog]
            )

        response = self.client.get(
            path=reverse(
                'audit:audit-operations-detail', args=(audit_entities['audit_operations'][0].pk,)
            ),
            content_type="application/json",
        )
        assert response.status_code == 200
        obj_json = response.json()
        assert all(
            [obj_json[field] == self.default_auditlog[field] for field in self.default_auditlog]
        )

        response = self.client.get(
            path=reverse('audit:audit-logins-list'), content_type="application/json"
        ).json()
        assert response['count'] == num_entities
        assert response['results']
        for item in response['results']:
            assert all(
                [
                    item[field] == self.default_auditsession[field]
                    for field in self.default_auditsession
                ]
            )

        response = self.client.get(
            path=reverse('audit:audit-logins-detail', args=(audit_entities['audit_logins'][0].pk,)),
            content_type="application/json",
        )
        assert response.status_code == 200
        obj_json = response.json()
        assert all(
            [
                obj_json[field] == self.default_auditsession[field]
                for field in self.default_auditsession
            ]
        )

    def test_filters_operations(self):
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
            path=reverse('audit:audit-operations-list'), content_type="application/json"
        ).json()
        assert response['count'] == 5

        response = self.client.get(
            path=reverse('audit:audit-operations-list'),
            data={'object_type': 'cluster'},
            content_type="application/json",
        ).json()
        assert response['count'] == 2

        response = self.client.get(
            path=reverse('audit:audit-operations-list'),
            data={'object_name': object_name},
            content_type="application/json",
        ).json()
        assert response['count'] == 3

        response = self.client.get(
            path=reverse('audit:audit-operations-list'),
            data={'operation_type': 'update'},
            content_type="application/json",
        ).json()
        assert response['count'] == 3

        response = self.client.get(
            path=reverse('audit:audit-operations-list'),
            data={'operation_name': operation_name},
            content_type="application/json",
        ).json()
        assert response['count'] == 3

        response = self.client.get(
            path=reverse('audit:audit-operations-list'),
            data={'operation_result': 'fail'},
            content_type="application/json",
        ).json()
        assert response['count'] == 3

        response = self.client.get(
            path=reverse('audit:audit-operations-list'),
            data={'username': self.user_username},
            content_type="application/json",
        ).json()
        assert response['count'] == 3

        response = self.client.get(
            path=reverse('audit:audit-operations-list'),
            data={'operation_date': date},
            content_type="application/json",
        ).json()
        assert response['count'] == 3

    def test_filters_logins(self):
        self._login_as(self.superuser_username, self.superuser_password)
        wrong_date = '1990-01-01'
        date = '2000-01-05'

        num_user_wrong_password = 4
        self._populate_audit_tables(
            user=self.user,
            login_result=AuditSessionLoginResult.WrongPassword,
            login_details={'some_test': 'details'},
            num=num_user_wrong_password,
        )

        num_superuser_success = 7
        audit_logins_superuser_success = self._populate_audit_tables(
            user=self.superuser,
            login_result=AuditSessionLoginResult.Success,
            login_details={'some_test': 'details'},
            num=num_superuser_success,
        )['audit_logins']

        response = self.client.get(
            path=reverse('audit:audit-logins-list'),
            content_type="application/json",
        ).json()
        assert response['count'] == num_user_wrong_password + num_superuser_success

        response = self.client.get(
            path=reverse('audit:audit-logins-list'),
            data={'username': self.user_username},
            content_type="application/json",
        ).json()
        assert response['count'] == num_user_wrong_password

        response = self.client.get(
            path=reverse('audit:audit-logins-list'),
            data={'login_result': AuditSessionLoginResult.Success.value},
            content_type="application/json",
        ).json()
        assert response['count'] == num_superuser_success

        response = self.client.get(
            path=reverse('audit:audit-logins-list'),
            data={'login_date': wrong_date},
            content_type="application/json",
        ).json()
        assert response['count'] == 0

        AuditSession.objects.filter(
            pk__in=[as_.pk for as_ in audit_logins_superuser_success]
        ).update(login_time=date)
        response = self.client.get(
            path=reverse('audit:audit-logins-list'),
            data={'login_date': date},
            content_type="application/json",
        ).json()
        assert response['count'] == num_superuser_success
