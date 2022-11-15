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

from django.shortcuts import render
from django.urls import include, path
from rest_framework.schemas import SchemaGenerator


def docs_md(request):
    return render(
        request,
        'docs-md/index.md',
        get_context(request, patterns=[path('api/v1/', include('api.urls'))]),
    )


def docs_html(request):
    return render(
        request,
        'docs-html/index.html',
        get_context(request, patterns=[path('api/v1/', include('api.urls'))]),
    )


def get_context(request, patterns=None):
    generator = SchemaGenerator(title='ArenaData Cluster Manager API', description=intro(), patterns=patterns)
    data = generator.get_schema(request, True)
    context = {
        'document': data,
        'request': request,
    }
    return context


def intro():
    return '''

__Version__: 1.0

# Intro

__Cluster__: Set of hosts and services

__Host__: Abstract container for components

__Service__: Set of components

__Component__: Peace of software

__HostComponent__: Map between hosts and components of services

__Task__: Service action at work. Consists of one or more jobs

__Job__: Minimal quantum of action. Run ansible playbook to do actual work

'''
