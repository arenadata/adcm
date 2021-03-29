#!/usr/bin/env python3
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

import json
import random
import string
import adcm.init_django		# pylint: disable=unused-import

from django.contrib.auth.models import User

from cm.logger import log
from cm.models import UserProfile, DummyData, CheckLog, GroupCheckLog
from cm.bundle import load_adcm
from cm.config import SECRETS_FILE
from cm.lock import unlock_all
from cm.status_api import Event


def random_string(strlen=10):
    return "".join([random.choice(string.ascii_letters) for _ in range(strlen)])


def create_status_user():
    user = "status"
    try:
        User.objects.get(username=user)
        return
    except User.DoesNotExist:
        pass
    password = random_string(40)
    token = random_string(40)
    User.objects.create_superuser(user, "", password)
    with open(SECRETS_FILE, 'w') as f:
        json.dump({
            'adcmuser': {
                'user': user,
                'password': password
            },
            'token': token}, f)
    log.info('Update secret file %s OK', SECRETS_FILE)


def create_dummy_data():
    DummyData.objects.create()


def clear_temp_tables():
    CheckLog.objects.all().delete()
    GroupCheckLog.objects.all().delete()


def init():
    log.info("Start initializing ADCM DB...")
    try:
        User.objects.get(username='admin')
    except User.DoesNotExist:
        User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    try:
        UserProfile.objects.get(login='admin')
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(login='admin')
    create_status_user()
    event = Event()
    unlock_all(event)
    clear_temp_tables()
    event.send_state()
    load_adcm()
    create_dummy_data()
    log.info("ADCM DB is initialized")


if __name__ == '__main__':
    init()
