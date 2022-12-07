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

from datetime import datetime
from secrets import randbelow

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone as tz

from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditSession,
    AuditSessionLoginResult,
)
from rbac.models import User


# pylint: disable=too-many-instance-attributes
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

        auditobject_kwargs = {
            **self.default_auditobject,
            **(auditobject_kwargs or self.default_auditobject),
        }
        auditlog_kwargs = {**self.default_auditlog, **(auditlog_kwargs or self.default_auditlog)}
        auditsession_kwargs = {
            **self.default_auditsession,
            **(auditsession_kwargs or self.default_auditsession),
        }

        for _ in range(num):
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
                auditlog_kwargs['operation_time'] = operation_time
            ret['audit_operations'].append(al)

            if 'user' not in auditsession_kwargs:
                auditsession_kwargs.update({'user': self.superuser})
            login_time = auditsession_kwargs.pop('login_time', None)
            as_ = AuditSession.objects.create(**auditsession_kwargs)
            if login_time is not None:
                as_.login_time = login_time
                as_.save()  # bypass auto_now_add=True
                auditsession_kwargs['login_time'] = login_time
            ret['audit_logins'].append(as_)
        return ret

    @staticmethod
    def _check_response(
        resp,
        template=None,
        list_view=True,
        expected_count=0,
        expected_status_code=200,
        should_fail=False,
        label='',
    ):
        def _get_date_func(datetime_str):
            return str(datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%SZ').date())

        # handle different field names (filters - json response / model creation - json response)
        _item_field_mutation = {
            'operation_time': _get_date_func,
            'login_time': _get_date_func,
        }
        _template_field_mutation = {
            'user': ('user_id', lambda x: x.pk),
        }

        assert resp.status_code == expected_status_code, label
        resp_json = resp.json()
        if should_fail:
            assert 'results' not in resp_json, label
            return

        resp_json = resp.json()

        if list_view:
            items = resp_json['results']
            assert resp_json['count'] == expected_count, label
        else:
            items = [resp_json]

        for item in items:
            template_mutations = {'delete': [], 'merge': {}}
            for field in template:
                if field in _item_field_mutation:
                    item[field] = _item_field_mutation[field](item[field])
                if field in _template_field_mutation:
                    template_mutations['delete'].append(field)
                    template_mutations['merge'].update(
                        {_template_field_mutation[field][0]: _template_field_mutation[field][1](template[field])}
                    )
            for field in template_mutations['delete']:
                del template[field]
            template = {**template, **template_mutations['merge']}
            assert all(item[field] == template[field] for field in template), label


class TestViews(TestBase):
    def _run_single_filter_test(self, url_path, filter_kwargs, default_template, kwargs_name, create_kwargs=None):
        num_filter_target = randbelow(11) + 5
        num_others = num_filter_target - randbelow(3) + 1

        populate_kwargs = {kwargs_name: create_kwargs or filter_kwargs, 'num': num_filter_target}
        self._populate_audit_tables(**populate_kwargs)
        self._populate_audit_tables(num=num_others)
        response = self.client.get(
            path=url_path,
            data=filter_kwargs,
            content_type="application/json",
        )
        self._check_response(
            response,
            template={**default_template, **(create_kwargs or filter_kwargs)},
            expected_count=num_filter_target,
        )
        self.tearDown()

    def test_audit_visibility_regular_user(self):
        self._login_as(self.user_username, self.user_password)
        audit_entities = self._populate_audit_tables(num=3)
        response = self.client.get(path=reverse('audit:auditlog-list'), content_type="application/json")
        self._check_response(response, expected_status_code=403, should_fail=True)

        response = self.client.get(
            path=reverse('audit:auditlog-detail', args=(audit_entities['audit_operations'][0].pk,)),
            content_type="application/json",
        )
        self._check_response(response, expected_status_code=403, should_fail=True)

        response = self.client.get(path=reverse('audit:auditsession-list'), content_type="application/json")
        self._check_response(response, expected_status_code=403, should_fail=True)

        response = self.client.get(
            path=reverse('audit:auditsession-detail', args=(audit_entities['audit_logins'][0].pk,)),
            content_type="application/json",
        )
        self._check_response(response, expected_status_code=403, should_fail=True)

    def test_audit_visibility_superuser(self):
        self._login_as(self.superuser_username, self.superuser_password)
        num_entities = 5
        audit_entities = self._populate_audit_tables(num=num_entities)
        response = self.client.get(path=reverse('audit:auditlog-list'), content_type="application/json")
        self._check_response(response, template=self.default_auditlog, expected_count=num_entities)

        response = self.client.get(
            path=reverse('audit:auditlog-detail', args=(audit_entities['audit_operations'][0].pk,)),
            content_type="application/json",
        )
        self._check_response(response, template=self.default_auditlog, expected_count=num_entities, list_view=False)

        response = self.client.get(path=reverse('audit:auditsession-list'), content_type="application/json")
        self._check_response(response, template=self.default_auditsession, expected_count=num_entities)

        response = self.client.get(
            path=reverse('audit:auditsession-detail', args=(audit_entities['audit_logins'][0].pk,)),
            content_type="application/json",
        )
        self._check_response(
            response,
            template=self.default_auditsession,
            expected_count=num_entities,
            list_view=False,
        )

    def test_filters_operations(self):
        self._login_as(self.superuser_username, self.superuser_password)
        url_operations = reverse('audit:auditlog-list')
        date = '2000-01-05'

        self._run_single_filter_test(
            url_operations,
            {'object_type': AuditObjectType.Bundle},
            self.default_auditlog,
            'auditobject_kwargs',
        )
        self._run_single_filter_test(
            url_operations,
            {'object_name': 'new_object_name'},
            self.default_auditlog,
            'auditobject_kwargs',
        )

        self._run_single_filter_test(
            url_operations,
            {'operation_type': AuditLogOperationType.Update},
            self.default_auditlog,
            'auditlog_kwargs',
        )
        self._run_single_filter_test(
            url_operations,
            {'operation_name': 'new_operation_name'},
            self.default_auditlog,
            'auditlog_kwargs',
        )
        self._run_single_filter_test(
            url_operations,
            {'operation_result': AuditLogOperationResult.Fail},
            self.default_auditlog,
            'auditlog_kwargs',
        )

        self._run_single_filter_test(
            url_operations,
            {'operation_date': date},
            self.default_auditlog,
            'auditlog_kwargs',
            create_kwargs={'operation_time': date},
        )

        self._run_single_filter_test(
            url_operations,
            {'username': self.user_username},
            self.default_auditlog,
            'auditlog_kwargs',
            create_kwargs={'user': self.user},
        )

        # filter by today
        today = str(tz.now().date())
        not_today = '1999-01-01'
        num_new_entities = 3
        self._populate_audit_tables(num=num_new_entities)
        self._populate_audit_tables(num=1, auditlog_kwargs={'operation_time': not_today})
        response = self.client.get(
            path=url_operations,
            data={'operation_date': today},
            content_type="application/json",
        )
        self._check_response(response, self.default_auditlog, expected_count=num_new_entities)

    def test_filters_logins(self):
        self._login_as(self.superuser_username, self.superuser_password)
        url_logins = reverse('audit:auditsession-list')
        date = '2000-01-05'

        self._run_single_filter_test(
            url_logins,
            {'username': self.user_username},
            self.default_auditsession,
            'auditsession_kwargs',
            create_kwargs={'user': self.user},
        )

        self._run_single_filter_test(
            url_logins,
            {'login_result': AuditSessionLoginResult.UserNotFound},
            self.default_auditsession,
            'auditsession_kwargs',
        )

        # test with None details
        self._run_single_filter_test(
            url_logins,
            {'login_result': AuditSessionLoginResult.UserNotFound},
            self.default_auditsession,
            'auditsession_kwargs',
            create_kwargs={
                'login_details': None,
                'login_result': AuditSessionLoginResult.UserNotFound,
            },
        )

        self._run_single_filter_test(
            url_logins,
            {'login_date': date},
            self.default_auditsession,
            'auditsession_kwargs',
            create_kwargs={'login_time': date},
        )

        # filter by today
        today = str(tz.now().date())
        not_today = '1999-01-01'
        num_new_entities = 3
        self._populate_audit_tables(num=num_new_entities)
        self._populate_audit_tables(num=1, auditsession_kwargs={'login_time': not_today})
        response = self.client.get(
            path=url_logins,
            data={'login_date': today},
            content_type="application/json",
        )
        self._check_response(response, self.default_auditsession, expected_count=num_new_entities)
