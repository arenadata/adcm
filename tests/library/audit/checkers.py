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

"""Checkers are processors of audit log scenarios after they've been parsed"""

import pprint
from dataclasses import fields
from typing import Callable, Dict, List, Optional

import allure
from adcm_client.audit import AuditOperation
from adcm_client.objects import ADCMClient
from tests.library.audit.operations import Operation, convert_to_operations
from tests.library.audit.readers import ParsedAuditLog


class AuditLogChecker:
    """
    This checker configures itself to process audit log scenario based on its settings
    and then allows you to check the scenario when it happened in the system.
    """

    # Function to "drop" first N log records based on `start-from-first` option
    cut_to_start: Callable[[Operation, List[AuditOperation]], List[AuditOperation]]

    # Function to check that next audit log is correct based on `process-type` option
    # This function returns new list of operations on which `check_next` should be called next time
    # ! Empty collection of AuditOperation should never be passed
    check_next: Callable[[Operation, List[AuditOperation]], List[AuditOperation]]

    def __new__(cls, expected_logs: ParsedAuditLog):
        obj = super().__new__(cls)
        obj.cut_to_start = {
            'record': lambda _, actual_records: actual_records[:],
            'matched': _get_records_from_first_matched,
        }.pop(expected_logs.settings.start_from_first, None)
        if obj.cut_to_start is None:
            raise KeyError(
                f'No function specified for start-from-first option: "{expected_logs.settings.start_from_first}"'
            )
        obj.check_next = {
            'exact': _next_should_match,
            'sequence': _following_should_match,
            'presence': _one_of_should_match,
        }.pop(expected_logs.settings.process_type, None)
        if obj.check_next is None:
            raise KeyError(f'No function specified for process-type option: "{expected_logs.settings.process_type}"')
        return obj

    def __init__(self, expected_logs: ParsedAuditLog):
        self._raw_operations = expected_logs.operations
        if not self._raw_operations:
            raise ValueError('There should be at least 1 operation to check')
        # default username-id map
        self._user_map: Dict[str, int] = {'admin': 2, 'status': 3, 'system': 4}
        self._expected_logs = expected_logs
        self._operation_defaults = expected_logs.defaults

    @allure.step('Check that audit records match the scenario')
    def check(self, audit_records: List[AuditOperation]):
        """
        Check if given audit records matches the scenario.

        Note that given audit records are sorted by `operation_time`.
        """
        sorted_audit_records = sorted(audit_records, key=lambda rec: rec.operation_time)
        total_amount = len(sorted_audit_records)
        operations = convert_to_operations(
            self._raw_operations, self._operation_defaults.username, self._operation_defaults.result, self._user_map
        )
        first_expected_operation = operations[0]
        try:
            suitable_records = self.cut_to_start(first_expected_operation, sorted_audit_records)
        except AssertionError:
            self._attach_all_operations_and_expected_one(sorted_audit_records, first_expected_operation)
            raise
        last_found_ind = -1
        last_processed_operation = None
        for i, expected_operation in enumerate(operations):
            try:
                suitable_records = self.check_next(expected_operation, suitable_records)
            except AssertionError:
                self._attach_all_operations_and_expected_one(sorted_audit_records, expected_operation)
                if last_processed_operation:
                    allure.attach(
                        pprint.pformat(last_processed_operation),
                        # not i - 1, because it's "natural" position of item
                        name=f'Last processed operation #{i} (as log #{last_found_ind})',
                        attachment_type=allure.attachment_type.JSON,
                    )
                raise
            else:
                last_processed_operation = expected_operation
                # last_found_ind can't be "correctly" calculated for "one of should match"
                last_found_ind = total_amount - len(suitable_records) - 1

    def set_user_map(
        self, client_: Optional[ADCMClient] = None, user_id_map_: Optional[Dict[str, int]] = None, **user_ids: int
    ) -> None:
        """
        When there are custom users in the scenario, you should use this method to provide full user list.
        It is used to match usernames with ids.

        Only one source is used in priority: client, user_id_map, user_ids.

        Examples:

        checker.set_user_map(user_id_map_={'admin': 2, 'status': 3, 'new_user': 5})

        checker.set_user_map(admin=2, status=3, new_user=5)
        """
        if client_:
            self._user_map = {u.username: u.id for u in client_.user_list()}
            return
        if user_id_map_:
            if not (
                all(isinstance(k, str) for k in user_id_map_.keys())
                and all(isinstance(v, int) for v in user_id_map_.values())
            ):
                raise TypeError(
                    'All keys in `user_id_map_` should be strings (usernames) and all values should be integers (ids)'
                )
            self._user_map = {**user_id_map_}
            return
        if user_ids:
            if not all(isinstance(v, int) for v in user_ids.values()):
                raise TypeError('All values of `user_ids` should be integers (ids)')
            self._user_map = {**user_ids}
            return
        raise RuntimeError('Either `client_`, `user_id_map_` or kwargs should be provided to populate user map')

    def _attach_all_operations_and_expected_one(
        self, audit_records: List[AuditOperation], expected_operation: Operation
    ):
        allure.attach(
            '\n\n'.join(
                f'{ind}\n'
                + ',\n'.join(f'{f.name}={getattr(rec, f.name)}' for f in fields(Operation) if hasattr(rec, f.name))
                for ind, rec in enumerate(audit_records)
            ),
            name='Audit records from API',
            attachment_type=allure.attachment_type.TEXT,
        )
        allure.attach(
            pprint.pformat(expected_operation),
            name='Not found operation',
            attachment_type=allure.attachment_type.JSON,
        )


def _get_records_from_first_matched(
    expected_operation: Operation, actual_records: List[AuditOperation]
) -> List[AuditOperation]:
    for ind, record in enumerate(actual_records):
        if expected_operation.is_equal_to(record):
            return actual_records[ind:]
    raise AssertionError(f'None of records matched {expected_operation}')


def _next_should_match(expected_operation: Operation, actual_records: List[AuditOperation]) -> List[AuditOperation]:
    record_to_check = actual_records[0]
    assert expected_operation.is_equal_to(record_to_check), (
        'Incorrect next element found when checking audit logs.\n\n'
        f'Expected: {expected_operation}\n\n'
        f'Actual: {record_to_check}'
    )
    return actual_records[1:]


def _following_should_match(
    expected_operation: Operation, actual_records: List[AuditOperation]
) -> List[AuditOperation]:
    for ind, record in enumerate(actual_records):
        if expected_operation.is_equal_to(record):
            return actual_records[ind + 1 :]
    raise AssertionError(f'Failed to find next element matching operation: {expected_operation}')


def _one_of_should_match(expected_operation: Operation, actual_records: List[AuditOperation]) -> List[AuditOperation]:
    for ind, record in enumerate(actual_records):
        if expected_operation.is_equal_to(record):
            return actual_records[0:ind] + actual_records[ind + 1 :]
    raise AssertionError(f'None of records matched operation: {expected_operation}')
