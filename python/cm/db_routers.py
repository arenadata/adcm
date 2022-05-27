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


# pylint: disable=protected-access


ALWAYS_ALLOW_MIGRATE_APP_LABELS = ('sites', 'contenttypes', 'auth')


class BackgroundTasksRouter:
    app_label = 'background_task'
    db_name = 'background_tasks'

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.app_label:
            return self.db_name
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.app_label:
            return self.db_name
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (  # pylint: disable=consider-using-in
            obj1._meta.app_label == self.app_label or obj2._meta.app_label == self.app_label
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in ALWAYS_ALLOW_MIGRATE_APP_LABELS:
            return True
        if app_label == self.app_label:
            return db == self.db_name
        return None


class DefaultRouter:
    db_name = 'default'

    def db_for_read(self, model, **hints):
        return self.db_name

    def db_for_write(self, model, **hints):
        return self.db_name

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in ALWAYS_ALLOW_MIGRATE_APP_LABELS:
            return True
        return db == self.db_name
