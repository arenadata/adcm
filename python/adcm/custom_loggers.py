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

from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from tempfile import gettempdir
import fcntl


class LockingTimedRotatingFileHandler(TimedRotatingFileHandler):
    def emit(self, record):
        lock_file_path = Path(gettempdir(), Path(self.baseFilename).name).with_suffix(".lock")

        with lock_file_path.open(mode="wt", encoding="utf-8") as lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                super().emit(record)
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
