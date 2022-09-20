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

from __future__ import unicode_literals

from django.contrib.auth import login
from django.shortcuts import render
from rest_framework.authtoken.models import Token

from cm import config
from cm.logger import logger
from cm.models import UserProfile


def index(request):
    return render(request, "index.html", {})


def ws_test(request, ws_type="event", dev="production"):
    context = {"local": dev, "type": ws_type, "token": config.STATUS_SECRET_KEY}

    return render(request, "ws.html", context)


def get_token(strategy, user, response, *args, **kwargs):
    try:
        token = Token.objects.get(user=user)
    except Token.DoesNotExist:
        logger.info("Create auth token for social user %s", user)
        token = Token(user=user)
        token.key = token.generate_key()
        token.save()
        up = UserProfile.objects.create(login=user.username)
        up.save()
        user.is_superuser = True
        user.save()

    logger.info("authorize social user %s", user)
    login(strategy.request, user, backend="django.contrib.auth.backends.ModelBackend")

    return render(strategy.request, "token.html", {"login": user.username, "token": token.key})


def error(request, msg):
    context = {"error_message": msg}

    return render(request, "error.html", context)
