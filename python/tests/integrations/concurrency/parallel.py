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
Running calls in parallel threads, so races between them reproduce deterministically.

Every call (plugin executor, internal script, etc.) is run in its own thread,
hence with its own DB connection (Django keeps connections per thread).
Every call has its own sync point (`SyncedCall.sync_before`), shared or different from siblings' ones:
calls meet at the rendezvous, each right before the first call of its own sync point,
so whatever a call reads before it is read before any sibling writes:
without a fix race is reproduced every time, not by chance.

When a fix serializes calls with a lock (advisory lock, `select_for_update`, etc.),
the call that took the lock waits at the rendezvous, while siblings wait for the lock in Postgres and can't arrive.
Waiting calls are released as soon as every call that isn't at the rendezvous waits for a lock in Postgres,
which is checked with `pg_blocking_pids`: blocked calls can't arrive anyway, whoever holds their locks
(the waiting calls, directly or through other blocked ones, or an outsider), so there's nothing to wait for.
Serialization is proven by Postgres rather than by waiting for some time (see `CallOutcome.serialized_by_lock`).

How it works:
1. Every distinct sync point is patched with `_wait_for_siblings_then_call` for the duration of the run.
   Thread-local state tells which call the current thread runs, so only the call that owns the sync point
   waits at the rendezvous, on the first call of it.
2. Every call is run in its own thread (`_run`): it registers backend pid of its connection at the rendezvous,
   runs the call, records the result or the error in its `CallOutcome`, marks itself finished
   and closes its connections.
   Outcomes are created before threads are started, since the rendezvous sets flags of calls that are still running.
3. The rendezvous (`_Rendezvous`) is opened once and for all, letting every call through, when:
   - no call is pending (each one has arrived or finished): `synchronized` is set, if all of them have arrived;
   - every pending call waits for a lock in Postgres: `serialized_by_lock` is set for the waiting and the blocked calls;
   - `sync_timeout` has passed since a call has arrived: no flag is set, the race may be not reproduced.
4. Main thread waits for threads until `timeout` passes, meanwhile, while someone waits at the rendezvous,
   it checks `pg_blocking_pids` of pending calls every `LOCK_POLL_INTERVAL` (`_release_blocked`).
   Calls that aren't finished in time are reported with `TimeoutError`, but not stopped: their threads are daemons.

Caveats:
- meant for `TransactionTestCase`: data of `TestCase` isn't committed, so threads won't see it;
- sync points are patched for the whole process, but only the thread a sync point belongs to waits on it,
  only once (on the first call); calls of siblings' sync points are passed through;
  sync point should be a function or an instance method;
- locks are detected for "default" database by backend pid of call's connection, taken when the call is started,
  so waits invisible to Postgres (python locks, reconnected connection, etc.) release waiting calls
  only by `sync_timeout`, while a wait for a lock of any session counts, not only of siblings;
- call that finished without reaching its sync point isn't waited for by siblings.
"""

from collections.abc import Callable, Collection, Iterable
from contextlib import ExitStack
from dataclasses import dataclass
from functools import partial
from pkgutil import resolve_name
from typing import Generic, TypeVar
from unittest import mock
import time
import threading

from django.db import connections

T = TypeVar("T")

# long enough for siblings to reach the rendezvous on a loaded machine,
# short enough not to slow down much cases where calls are serialized in a way invisible to Postgres
SYNC_TIMEOUT = 5
# limit for the whole run, exceeding it means calls hang (e.g. wait for a lock held by test's own connection)
CALL_TIMEOUT = 60
# how often locks of calls that haven't reached the rendezvous are checked, while someone waits there
LOCK_POLL_INTERVAL = 0.005


@dataclass(slots=True)
class CallOutcome(Generic[T]):
    result: T | None = None
    error: BaseException | None = None
    # whether all calls met at their sync points: whatever every call read before it, it read before any write
    synchronized: bool = False
    # whether calls didn't meet since every one that hadn't arrived was blocked by a lock in Postgres
    # (supposedly held by the ones waiting at sync points), it's set for both the waiting and the blocked calls
    serialized_by_lock: bool = False


@dataclass(slots=True, frozen=True)
class SyncedCall(Generic[T]):
    func: Callable[[], T]
    # path to patch the same way as for `mock.patch` (e.g. "cm.models.ConfigLog.save")
    sync_before: str


class _ThreadState(threading.local):
    # index of the call in `run_concurrently`, `None` for threads not started by it
    index: int | None = None
    sync_before: str | None = None


@dataclass(slots=True)
class _Participant:
    outcome: CallOutcome
    # backend pid of call's DB connection, unknown until the call is started
    pid: int | None = None
    # reached its sync point: waits at the rendezvous, or has passed it once it's opened
    arrived: bool = False
    # returned or raised, whether it has arrived or not
    finished: bool = False

    @property
    def is_pending(self) -> bool:
        """Neither at the rendezvous, nor finished"""

        return not (self.arrived or self.finished)


class _Rendezvous:
    """
    Where calls of `run_concurrently` meet.

    Call waits at it until every sibling arrives or finishes,
    or until siblings that haven't arrived are blocked by locks in Postgres (see `release_blocked`),
    or until `timeout` passes since its arrival.
    Once opened, it lets every call through without waiting.
    State is guarded by the condition, since it's changed by threads of calls and checked by the main thread.
    """

    def __init__(self, outcomes: Iterable[CallOutcome], timeout: float) -> None:
        self._participants = tuple(_Participant(outcome=outcome) for outcome in outcomes)
        self._timeout = timeout
        self._condition = threading.Condition()
        self._is_open = False

    def start(self, index: int, pid: int) -> None:
        with self._condition:
            self._participants[index].pid = pid

    def finish(self, index: int) -> None:
        with self._condition:
            self._participants[index].finished = True
            self._condition.notify_all()

    def arrive(self, index: int) -> None:
        """Wait for siblings, repeated calls of the same participant pass through"""

        with self._condition:
            participant = self._participants[index]
            if participant.arrived:
                return

            participant.arrived = True
            self._condition.notify_all()

            deadline = time.monotonic() + self._timeout
            while not self._is_open:
                if not any(sibling.is_pending for sibling in self._participants):
                    if all(sibling.arrived for sibling in self._participants):
                        for sibling in self._participants:
                            sibling.outcome.synchronized = True

                    self._open()
                elif (remaining := deadline - time.monotonic()) > 0:
                    self._condition.wait(timeout=remaining)
                else:
                    # pending siblings are neither seen blocked, nor arrived: they may be just slow
                    self._open()

    def get_pending_pids(self) -> set[int] | None:
        """
        Pids of the pending calls, if they have to be checked for locks.
        `None` if nobody waits, nobody is pending or some pending call isn't started yet.
        """

        with self._condition:
            if self._is_open or not any(participant.arrived for participant in self._participants):
                return None

            pending = [participant for participant in self._participants if participant.is_pending]
            pending_pids = {participant.pid for participant in pending if participant.pid is not None}
            if not pending or len(pending_pids) != len(pending):
                return None

            return pending_pids

    def release_blocked(self, blocked_pids: Collection[int]) -> None:
        """Open the rendezvous, if every pending call is blocked (state is re-checked, since it may change)"""

        with self._condition:
            pending = [participant for participant in self._participants if participant.is_pending]
            if self._is_open or not pending or any(participant.pid not in blocked_pids for participant in pending):
                return

            for participant in self._participants:
                if participant.arrived or participant.pid in blocked_pids:
                    participant.outcome.serialized_by_lock = True

            self._open()

    def _open(self) -> None:
        self._is_open = True
        self._condition.notify_all()


def run_concurrently(
    *calls: SyncedCall[T], sync_timeout: float = SYNC_TIMEOUT, timeout: float = CALL_TIMEOUT
) -> tuple[CallOutcome[T], ...]:
    """
    Run `calls` in separate threads, each waiting for others before the first call of its `sync_before`.

    `sync_timeout` limits how long a call waits for siblings at the rendezvous, then it goes on without them.
    `timeout` limits the whole run.

    Outcomes are returned in the order of `calls`, exceptions are returned rather than raised.
    `TimeoutError` is raised if calls aren't finished in `timeout` seconds.
    """

    num_calls = len(calls)
    if num_calls < 2:
        message = f"At least 2 calls are required to run them concurrently, got {num_calls}"
        raise ValueError(message)

    outcomes = tuple(CallOutcome() for _ in calls)
    rendezvous = _Rendezvous(outcomes=outcomes, timeout=sync_timeout)
    state = _ThreadState()

    threads = tuple(
        threading.Thread(
            target=_run, args=(i, call, outcome, rendezvous, state), name=f"concurrent-call-{i}", daemon=True
        )
        for i, (call, outcome) in enumerate(zip(calls, outcomes, strict=True))
    )

    with ExitStack() as patches:
        # sync point shared by calls is patched once
        for sync_before in dict.fromkeys(call.sync_before for call in calls):
            wait_then_call_original = partial(
                _wait_for_siblings_then_call, sync_before, resolve_name(sync_before), rendezvous, state
            )
            # autospec makes patched method receive `self` the same way the original one does
            patches.enter_context(mock.patch(sync_before, autospec=True, side_effect=wait_then_call_original))

        deadline = time.monotonic() + timeout

        for thread in threads:
            thread.start()

        # main thread checks locks of calls while waiting for them, so calls themselves don't query anything extra
        while (alive := [thread for thread in threads if thread.is_alive()]) and (
            remaining := deadline - time.monotonic()
        ) > 0:
            _release_blocked(rendezvous)
            alive[0].join(timeout=min(LOCK_POLL_INTERVAL, remaining))

    if hanging := [thread.name for thread in threads if thread.is_alive()]:
        message = f"Calls aren't finished in {timeout}s: {', '.join(hanging)}"
        raise TimeoutError(message)

    return outcomes


def _wait_for_siblings_then_call(
    sync_before: str, original: Callable, rendezvous: _Rendezvous, state: _ThreadState, /, *args, **kwargs
):
    """Replaces `sync_before`: thread of `run_concurrently` it belongs to waits for siblings on its first call"""

    if state.index is not None and state.sync_before == sync_before:
        rendezvous.arrive(state.index)

    return original(*args, **kwargs)


def _run(
    index: int, call: SyncedCall[T], outcome: CallOutcome[T], rendezvous: _Rendezvous, state: _ThreadState
) -> None:
    """Target of thread started by `run_concurrently`: runs the call and records its outcome"""

    state.index = index
    state.sync_before = call.sync_before

    try:
        rendezvous.start(index=index, pid=_get_backend_pid())
        outcome.result = call.func()
    except BaseException as e:  # noqa: BLE001
        outcome.error = e
    finally:
        # siblings don't wait for the call that won't reach its sync point anymore
        rendezvous.finish(index)

        # connections are per thread, so only the ones opened by this call are closed
        connections.close_all()


def _release_blocked(rendezvous: _Rendezvous) -> None:
    """Open the rendezvous, if Postgres shows that every call that hasn't arrived waits for a lock"""

    if (pending := rendezvous.get_pending_pids()) is None:
        return

    if blocked := _get_blocked(pending):
        rendezvous.release_blocked(blocked_pids=blocked)


def _get_blocked(pids: Collection[int]) -> set[int]:
    """Given pids that wait for locks held by other sessions (works for any lock: advisory, row, etc.)"""

    with connections["default"].cursor() as cursor:
        cursor.execute(
            "SELECT pid FROM unnest(%s::integer[]) AS pid WHERE cardinality(pg_blocking_pids(pid)) > 0", [list(pids)]
        )
        return {pid for (pid,) in cursor.fetchall()}


def _get_backend_pid() -> int:
    with connections["default"].cursor() as cursor:
        cursor.execute("SELECT pg_backend_pid()")
        (pid,) = cursor.fetchone()

    return pid
