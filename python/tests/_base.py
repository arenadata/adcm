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

from itertools import chain
from shutil import rmtree

import django.test

from tests.dependencies import prepare_process_bound_directories


class WithIndependentDirectories:
    """
    Prepares directories for parallel tests run.

    On `__init_subclass__`:
    1. Cached `Directories` are ASSIGNED for current process
    2. Django settings overriden for each child class with same directories values (compatibility reasons)

    Important:
    - assigned directories aren't actually created (`_create_directories_on_fs` is used for that)
    - method used is bound to DI of test run (that's why it's cached)
    - caching means that `__init_subclass__` must be called in each process again
      (=> `fork` process creation method is no good)
    - code is required to be in `__init_subclass__` as lesser evil to metaclass / test hierarchy changes
      due to `override_settings` being used
    - once legacy using `settings.*_DIR` directly is gone, this approach can be revisited
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        cls.directories = prepare_process_bound_directories()
        cls.temporary_directories = {
            "STACK_DIR": cls.directories.stack,
            "DATA_DIR": cls.directories.data,
            "BUNDLE_DIR": cls.directories.bundles,
            "DOWNLOAD_DIR": cls.directories.downloads,
            "RUN_DIR": cls.directories.run,
            "FILE_DIR": cls.directories.files,
            "LOG_DIR": cls.directories.logs,
            "VAR_DIR": cls.directories.secrets,
            "TMP_DIR": cls.directories.temp,
        }
        django.test.override_settings(**cls.temporary_directories)(cls)

    @classmethod
    def _create_directories_on_fs(cls):
        # actually init temp directories
        for directory in cls.temporary_directories.values():
            directory.mkdir(exist_ok=True, parents=True)

    @classmethod
    def _clean_directories(cls):
        directories_to_clean = (
            cls.directories.bundles,
            cls.directories.downloads,
            cls.directories.files,
            cls.directories.logs,
            cls.directories.run,
        )

        for item in chain.from_iterable(path.iterdir() for path in directories_to_clean):
            if item.is_dir():
                rmtree(item)
            elif item.name != ".gitkeep":
                item.unlink()
