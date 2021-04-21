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

# pylint: disable=duplicate-except,attribute-defined-outside-init

import rest_framework
import django.contrib.auth

from rest_framework import routers, status
from rest_framework.authtoken.models import Token
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

import api.serializers
import cm.api
import cm.config as config
import cm.job
import cm.stack
import cm.status_api
from cm.models import JobLog, TaskLog
from adcm.settings import ADCM_VERSION
from api.api_views import GenericAPIPermView


class APIRoot(routers.APIRootView):
    """
    Arenadata Chapel API
    """
    permission_classes = (rest_framework.permissions.AllowAny,)
    api_root_dict = {
        'adcm': 'adcm',
        'cluster': 'cluster',
        'profile': 'profile-list',
        'provider': 'provider',
        'host': 'host',
        'service': 'service',
        'component': 'component',
        'job': 'job',
        'stack': 'stack',
        'stats': 'stats',
        'task': 'task',
        'token': 'token',
        'logout': 'logout',
        'user': 'user-list',
        'group': 'group-list',
        'role': 'role-list',
        'info': 'adcm-info',
    }


class NameConverter:
    regex = cm.stack.NAME_REGEX

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


class GetAuthToken(GenericAPIView):
    authentication_classes = (rest_framework.authentication.TokenAuthentication,)
    permission_classes = (rest_framework.permissions.AllowAny,)
    serializer_class = api.serializers.AuthSerializer

    def post(self, request, *args, **kwargs):
        """
        Provide authentication token

        HTTP header for authorization:

        ```Authorization: Token XXXXX```
        """
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _created = Token.objects.get_or_create(user=user)
        django.contrib.auth.login(
            request, user, backend='django.contrib.auth.backends.ModelBackend'
        )
        return Response({'token': token.key})


class LogOut(GenericAPIView):
    serializer_class = api.serializers.LogOutSerializer

    def post(self, request, *args, **kwargs):
        """
        Logout user from Django session
        """
        django.contrib.auth.logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ADCMInfo(GenericAPIView):
    permission_classes = (rest_framework.permissions.AllowAny,)
    serializer_class = api.serializers.EmptySerializer

    def get(self, request):
        """
        General info about ADCM
        """
        return Response({
            'adcm_version': ADCM_VERSION,
            'google_oauth': cm.api.has_google_oauth()
        })


class Stats(GenericAPIPermView):
    queryset = JobLog.objects.all()
    serializer_class = api.serializers.StatsSerializer

    def get(self, request):
        """
        Statistics
        """
        obj = JobLog(id=1)
        serializer = self.serializer_class(obj, context={'request': request})
        return Response(serializer.data)


class JobStats(GenericAPIPermView):
    queryset = JobLog.objects.all()
    serializer_class = api.serializers.EmptySerializer

    def get(self, request, job_id):
        """
        Show jobs stats
        """
        jobs = self.get_queryset().filter(id__gt=job_id)
        data = {
            config.Job.FAILED: jobs.filter(status=config.Job.FAILED).count(),
            config.Job.SUCCESS: jobs.filter(status=config.Job.SUCCESS).count(),
            config.Job.RUNNING: jobs.filter(status=config.Job.RUNNING).count(),
        }
        return Response(data)


class TaskStats(GenericAPIPermView):
    queryset = TaskLog.objects.all()
    serializer_class = api.serializers.EmptySerializer

    def get(self, request, task_id):
        """
        Show tasks stats
        """
        tasks = self.get_queryset().filter(id__gt=task_id)
        data = {
            config.Job.FAILED: tasks.filter(status=config.Job.FAILED).count(),
            config.Job.SUCCESS: tasks.filter(status=config.Job.SUCCESS).count(),
            config.Job.RUNNING: tasks.filter(status=config.Job.RUNNING).count(),
        }
        return Response(data)
