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

"""ADCM database manipulations"""


import datetime
from dataclasses import dataclass
from typing import Callable, Collection, Optional, Tuple, Union

from docker.models.containers import Container

# !===== Query =====!


class Query:
    """
    Query builder aimed to prepare queries for ADCM database.

    It's now just a prototype, so use with caution.
    """

    table: str
    operation: str

    _build_statement: Optional[Callable[[], str]]

    def __init__(self, table: str):
        self.table = table

        self.operation = ''
        self._build_statement = None

        self._where_clause = ''
        self._set_clause = ''

    def build(self) -> str:
        """Get string representation of a query"""
        if self._build_statement is None:
            raise ValueError('Undefined type of a query')
        return self._build_statement()

    def update(self, fields: Collection[Tuple[str, Union[int, str, datetime.datetime]]]) -> 'Query':
        """Prepare query to become an UPDATE operation"""
        self._build_statement = self._build_update
        self.operation = 'UPDATE'
        self._make_set_clause(fields)
        return self

    def where(self, *, concat_with: str = 'AND', **kwargs) -> 'Query':
        """Add WHERE clause to a query"""
        self._raise_if_already_set(self._where_clause, 'WHERE')
        where_ = []
        for field, value in kwargs.items():
            where_.append(
                f'{self.table}.{field} in ({", ".join(map(str, value))})'
                if isinstance(value, Collection)
                else f'{self.table}.{field}={value}'
            )
        joined_where = f" {concat_with} ".join(where_)
        self._where_clause = f'WHERE {joined_where}'
        return self

    def _make_set_clause(self, fields: Collection[Tuple[str, Union[int, str, datetime.datetime]]]):
        self._raise_if_already_set(self._set_clause, 'SET')
        set_ = []
        for field, value in fields:
            if isinstance(value, int):
                value_repr = str(value)
            elif isinstance(value, str):
                value_repr = f'\"{value}\"'
            elif isinstance(value, datetime.datetime):
                value_repr = f'\"{value.isoformat()}\"'
            else:
                raise ValueError(f'Incorrect type of value for a "SET" clause: {type(value)}')
            set_.append(f'{field} = {value_repr}')
        self._set_clause = f'SET {", ".join(set_)}'

    def _build_update(self) -> str:
        return f'UPDATE {self.table}\n{self._set_clause}\n{self._where_clause}'

    def _raise_if_already_set(self, clause: str, clause_name: str):
        if clause:
            raise ValueError(f'{clause_name} clause is already set: {self._set_clause}')


# !===== Query Executioner =====!

STATEMENT_TEMPLATE = """
import sqlite3
conn = sqlite3.connect('/adcm/data/var/cluster.db')
try:
    with conn:
        conn.execute('{statement}')
finally:
    conn.close()
"""


@dataclass()
class QueryExecutioner:
    """
    First version of Query executioner
    that uploads the intermediate python script inside the container
    and then executes it inside the container.

    Use with caution.
    """

    adcm: Container

    _template = STATEMENT_TEMPLATE
    _script_name = '/adcm/data/exec_query.py'

    def exec(self, query: Query):
        """Execute given query via script inside the ADCM container"""
        statement = query.build()
        script_text = self._template.format(statement=statement.replace('\n', '  ')).replace('"', '\\"')
        self._should_be_success(self.adcm.exec_run(['sh', '-c', f'echo "{script_text}" > {self._script_name}']))
        self._should_be_success(self.adcm.exec_run(['python3', self._script_name]))

    def _should_be_success(self, exec_result: Tuple[int, bytes]):
        exit_code, output = exec_result
        if exit_code == 0:
            return
        raise ValueError(
            f'Command execution on ADCM container {self.adcm.name} failed:\n' f'Output: {output.decode("utf-8")}'
        )


# !===== Helpful functions =====!

CONFIG_LOG_TABLE = 'cm_configlog'
JOB_LOG_TABLE = 'cm_joblog'
TASK_LOG_TABLE = 'cm_tasklog'
LOG_STORAGE_TABLE = 'cm_logstorage'


def set_configs_date(adcm_db: QueryExecutioner, date: datetime.datetime, ids: Collection[int] = ()):
    """Set given date to all config logs or given configs directly in ADCM database"""
    query = Query(CONFIG_LOG_TABLE).update([('date', date)])
    if ids:
        query.where(id=ids)
    adcm_db.exec(query)


def set_jobs_date(adcm_db: QueryExecutioner, date: datetime.datetime, ids: Collection[int] = ()):
    """Set given date to start_date and finish_date of all jobs or given jobs directly in ADCM database"""
    query = Query(JOB_LOG_TABLE).update([('start_date', date), ('finish_date', date)])
    if ids:
        query.where(id=ids)
    adcm_db.exec(query)


def set_tasks_date(adcm_db: QueryExecutioner, date: datetime.datetime, ids: Collection[int] = ()):
    """Set given date to start_date and finish_date of all tasks or given tasks directly in ADCM database"""
    query = Query(TASK_LOG_TABLE).update([('start_date', date), ('finish_date', date)])
    if ids:
        query.where(id=ids)
    adcm_db.exec(query)


def set_job_directories_date(container: Container, date: datetime.datetime, ids: Collection[int]):
    """Set given date as last modified date for each directory in /adcm/data/run that are presented in ids"""
    strdate = date.strftime("%Y%m%d%H%M")
    for id_ in ids:
        exit_code, output = container.exec_run(['touch', '-t', strdate, f'/adcm/data/run/{id_}/'])
        if exit_code != 0:
            raise ValueError(
                f"Failed to set modification date ('{strdate}') to job dir with id {id_}.\n'"
                f"f'Output:\n{output.decode('utf-8')}"
            )
