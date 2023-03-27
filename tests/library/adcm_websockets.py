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

import asyncio
import json
from collections.abc import Collection
from datetime import datetime
from pprint import pformat
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

import allure
from adcm_pytest_plugin.utils import catch_failed
from websockets.legacy.client import WebSocketClientProtocol

from tests.library.types import WaitTimeout

WSMessageData = dict[str, Any]
MismatchReason = str | None


class EventMessage(NamedTuple):
    """
    Wrapper for checking contents of websocket event messages.
    `event` field is obligatory, because it's expected in each event message.
    Keys and values from `object_fields` are expected to be found inside the "object" fields.
    Keys that aren't in `object_fields`, but does exist in "object" are ignored.
    """

    event: str
    object_fields: dict[str, Any]

    def match(self, message: WSMessageData) -> tuple[bool, MismatchReason]:
        """
        Check that "event" and "object" fields match this object
        """
        actual_event = message.get("event", None)
        if actual_event != self.event:
            return False, f"incorrect event: {actual_event}"

        # if we don't want to check any of it then event comparison is enough
        if not self.object_fields:
            return True, None

        object_data = message.get("object", None)
        if object_data is None:
            return False, f'"object" key is absent in message: {message}'

        for field, expected_value in self.object_fields.items():
            if field not in object_data:
                return False, f'key "{field}" is absent in message: {message}'
            if object_data[field] != expected_value:
                return False, f'value of "{field}" is incorrect in message: {message}'

        return True, None


class ADCMWebsocket:
    """
    Helper for working with ADCM websocket event stream
    """

    _ws: WebSocketClientProtocol
    _default_timeout: float
    # datetime here is the UTC date of **adding** message to this list
    # not when the message was invoked
    _messages: list[tuple[datetime, WSMessageData]]

    def __init__(self, conn: WebSocketClientProtocol, timeout: WaitTimeout = 2):
        self._ws = conn
        self._default_timeout = timeout
        self._messages = []

    @allure.step("Wait for message from websocket for {timeout} seconds")
    async def get_message(self, timeout: WaitTimeout | None = None) -> WSMessageData:
        """
        Get message from websocket if it already exists or will come during timeout period.
        Raised exceptions aren't handled.

        :raises asyncio.TimeoutError: If no message is there for a timeout period.
        """
        timeout = timeout or self._default_timeout
        message = json.loads(await asyncio.wait_for(self._ws.recv(), timeout))
        self._messages.append((datetime.now(tz=ZoneInfo("UTC")), message))
        return message

    @allure.step("Get up to {max_messages} messages")
    async def get_messages(
        self,
        max_messages: int,
        single_msg_timeout: WaitTimeout = 1,
        break_on_first_fail: bool = True,
    ) -> list[WSMessageData]:
        """
        Get messages until `max_messages` is reached
        or retrieve message request timed out (if `break_on_first_fail` is `True`)
        """
        retrieved_messages = []
        for _ in range(max_messages):
            try:
                msg = await self.get_message(single_msg_timeout)
            except asyncio.TimeoutError:
                if break_on_first_fail:
                    break
            else:
                retrieved_messages.append(msg)
        with allure.step(f"Retrieved {len(retrieved_messages)} messages"):
            return retrieved_messages

    @allure.step('Get all "waiting" WS messages')
    async def get_waiting_messages(self) -> list[WSMessageData]:
        """
        Get all messages that currently can be received.

        This method retrieves messages until 1 sec read timeout occurs.
        """
        return await self._get_until_error([])

    async def expect_message(self, timeout=None) -> WSMessageData:
        """Get next message or raise `AssertionError` if it won't come on time"""
        timeout = timeout or self._default_timeout
        with catch_failed(asyncio.TimeoutError, f"Message was failed to be received in {timeout} seconds"):
            return await self.get_message(timeout)

    @allure.step("Ensure there won't come any WS message for a {timeout} seconds")
    async def no_message_for(self, timeout: WaitTimeout) -> None:
        """Check that there's no messages came during `timeout` period"""
        try:
            message = await self.get_message(timeout)
        except TimeoutError:
            pass
        else:
            raise AssertionError(f"At least one message came: {message}")

    # later we need checker for messages absence
    def check_messages_are_presented(
        self,
        expected: Collection[EventMessage],
        messages: Collection[WSMessageData] | None = None,
        check_order: bool = False,
    ):
        """
        Check if expected messages are presented in one of collections:
        1. Messages from `messages` argument, it isn't None and only None
        2. All read messages otherwise

        If `check_order` is True, then the messages should be presented in the order given in `expected`,
        so avoid using unordered collections like sets.
        When `messages` is not None, then its order is considered correct.

        WARNING: Current implementation ignores multiple matches if `check_order` is False.
                 So if you pass multiple expected messages with same `event` and `object_fields`,
                 `check_order` is False, and there's at least one message with that event and object data,
                 then check will be passed (ok).
        """
        messages_to_check = (
            messages if messages is not None else tuple(msg[0] for msg in sorted(self._messages, key=lambda x: x[0]))
        )
        if check_order:
            self._check_messages_ordered_presence(tuple(expected), tuple(messages_to_check))
        else:
            self._check_messages_unordered_presence(tuple(expected), tuple(messages_to_check))

    @allure.step("Check next incoming WS message")
    async def check_next_message_is(
        self,
        timeout: WaitTimeout | None = None,
        expected: EventMessage | None = None,
        event: str | None = None,
        **object_field,
    ) -> WSMessageData:
        """
        Expect next message to be presented and match the given one.

        Message in `expect` is preferred for keyword based arguments.
        Otherwise, you can provide `event` and kwargs to check "event" and "object" fields.
        """
        message = await self.expect_message(timeout or self._default_timeout)
        return self.check_message_is(message, expected, event, **object_field)

    @allure.step("Check next incoming WS message")
    async def check_next_message_is_not(
        self,
        timeout: WaitTimeout | None = None,
        wrong_message: EventMessage | None = None,
        event: str | None = None,
        **object_field,
    ) -> WSMessageData:
        """
        Expect next message to be presented and be different from the given one.

        Message in `expect` is preferred for keyword based arguments.
        Otherwise, you can provide `event` and kwargs to check "event" and "object" fields.
        """
        message = await self.expect_message(timeout or self._default_timeout)
        return self.check_message_is_not(message, wrong_message, event, **object_field)

    @allure.step("Check given WS message")
    def check_message_is(
        self,
        message_object: WSMessageData,
        expected: EventMessage | None = None,
        event: str | None = None,
        **object_field,
    ) -> WSMessageData:
        """
        Check messages matches.

        Message in `expect` is preferred for keyword based arguments.
        Otherwise, you can provide `event` and kwargs to check "event" and "object" fields.
        """
        if not isinstance(expected, EventMessage):
            if event is None:
                raise ValueError(
                    "Either provider `expected` as EventMessage instance or provide at least `event` as not None",
                )
            expected = EventMessage(event, object_fields=object_field)

        is_match, explanation = expected.match(message_object)
        if is_match:
            return

        allure.attach(
            pformat(expected),
            name="Expected message fields to be",
            attachment_type=allure.attachment_type.TEXT,
        )
        allure.attach(
            pformat(message_object),
            name="Actual message fields",
            attachment_type=allure.attachment_type.TEXT,
        )
        raise AssertionError(f"WS message is incorrect: {explanation}")

    @allure.step("Check given WS message")
    def check_message_is_not(
        self,
        message_object: WSMessageData,
        wrong_message: EventMessage | None = None,
        event: str | None = None,
        **object_field,
    ) -> WSMessageData:
        """
        Check messages doesn't match.

        Message in `expect` is preferred for keyword based arguments.
        Otherwise, you can provide `event` and kwargs to check "event" and "object" fields.
        """
        if not isinstance(wrong_message, EventMessage):
            if event is None:
                raise ValueError(
                    "Either provider `wrong_message` as EventMessage instance "
                    "or provide at least `event` as not None",
                )
            wrong_message = EventMessage(event=event, object_fields=object_field)

        is_match, _ = wrong_message.match(message_object)
        if not is_match:
            return

        allure.attach(
            pformat(wrong_message),
            name="Expected message fields not to be",
            attachment_type=allure.attachment_type.TEXT,
        )
        allure.attach(
            pformat(message_object),
            name="Actual message fields",
            attachment_type=allure.attachment_type.TEXT,
        )
        raise AssertionError("WS message should not match.\nCheck attachments for more details.")

    def _check_messages_ordered_presence(self, expected: tuple[EventMessage], messages: tuple[WSMessageData]):
        start_ind = 0
        for ind, expected_message in enumerate(expected):
            for i, presented_message in enumerate(messages[start_ind:]):
                if expected_message.match(presented_message)[0]:
                    start_ind = i + 1
                    break
            else:
                raise AssertionError(f"Message at #{ind} position was not found: {expected_message}")

    def _check_messages_unordered_presence(self, expected: tuple[EventMessage], messages: tuple[WSMessageData]):
        missing_messages = []
        for expected_message in expected:
            for presented_message in messages:
                if expected_message.match(presented_message)[0]:
                    break
            else:
                missing_messages.append(expected_message)
        if len(missing_messages) == 0:
            return
        allure.attach(
            pformat(missing_messages),
            name="Missing WS messages",
            attachment_type=allure.attachment_type.TEXT,
        )
        allure.attach(pformat(messages), name="Searched messages", attachment_type=allure.attachment_type.TEXT)
        raise AssertionError("Some of the expected WS messages were missing, check attachments for more details")

    async def _get_until_error(self, acc: list[WSMessageData]) -> list[WSMessageData]:
        try:
            acc.append(await self.get_message(1))
        except asyncio.TimeoutError:
            return acc
        else:
            return await self._get_until_error(acc)
