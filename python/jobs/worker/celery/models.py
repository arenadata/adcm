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

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class DBTables:
    taskmeta = "celery_taskmeta"
    heartbeat = "celery_workerheartbeat"


class Base(DeclarativeBase):
    pass


class WorkerHeartbeat(Base):
    __tablename__ = DBTables.heartbeat
    __table_args__ = (CheckConstraint("LENGTH(hostname) > 0", name="hostname_not_blank"),)

    hostname: Mapped[str] = mapped_column(String(length=100), nullable=False, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
