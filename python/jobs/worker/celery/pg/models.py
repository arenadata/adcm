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

"""
SQLAlchemy models backing the durable (non-fanout) side of the transport.

The layout intentionally mirrors kombu's ``sqlalchemy`` transport tables so an
existing ``kombu_message`` / ``kombu_queue`` store keeps working; the only
behavioural change is on the read path, where we claim rows with
``FOR UPDATE SKIP LOCKED`` instead of a plain ``visible`` flag flip.
"""

from __future__ import annotations

import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Sequence,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.schema import MetaData

metadata = MetaData()
ModelBase = declarative_base(metadata=metadata)


class Queue(ModelBase):
    """Named queue. One row per Celery queue (e.g. ``celery``)."""

    __tablename__ = "kombu_queue"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, Sequence("kombu_queue_id_seq"), primary_key=True, autoincrement=True)
    name = Column(String(200), unique=True)

    messages = relationship("Message", backref="queue", lazy="noload")

    def __init__(self, name: str) -> None:
        self.name = name


class Message(ModelBase):
    """A single durable message pending delivery on a queue."""

    __tablename__ = "kombu_message"
    __table_args__ = (
        Index("ix_kombu_message_queue_visible_id", "queue_id", "visible", "id"),
        {"sqlite_autoincrement": True},
    )

    id = Column(Integer, Sequence("kombu_message_id_seq"), primary_key=True, autoincrement=True)
    # kept for parity with kombu's sqla transport / at-least-once redelivery;
    # the SKIP LOCKED claim uses row locks, `visible` marks in-flight messages.
    visible = Column(Boolean, default=True, index=True)
    # as in the original kombu sqla transport: NULL on insert, stamped only by
    # the claim UPDATE (visible=False), so FIFO ordering falls through to `id`
    sent_at = Column("timestamp", DateTime, nullable=True, index=True, onupdate=datetime.datetime.now)
    payload = Column(Text, nullable=False)
    queue_id = Column(Integer, ForeignKey("kombu_queue.id", name="fk_kombu_message_queue"))

    def __init__(self, payload: str, queue: Queue) -> None:
        self.payload = payload
        self.queue = queue


class Binding(ModelBase):
    """
    Exchange->queue binding, shared across processes.

    kombu's virtual transports keep bindings in per-process memory, so a
    publisher in one process can't route a direct/topic message to a queue
    declared in another (e.g. a pidbox reply queue). Persisting bindings here —
    the way the redis transport persists them in redis — makes cross-process
    routing work, which is what lets Celery pidbox replies round-trip.
    """

    __tablename__ = "kombu_binding"
    __table_args__ = (UniqueConstraint("exchange", "routing_key", "queue", name="uq_kombu_binding"),)

    id = Column(Integer, Sequence("kombu_binding_id_seq"), primary_key=True, autoincrement=True)
    exchange = Column(String(200), nullable=False, index=True)
    routing_key = Column(String(200), nullable=False, default="")
    pattern = Column(String(400), nullable=False, default="")
    queue = Column(String(200), nullable=False, index=True)

    def __init__(self, exchange: str, routing_key: str, pattern: str, queue: str) -> None:
        self.exchange = exchange
        self.routing_key = routing_key
        self.pattern = pattern
        self.queue = queue
