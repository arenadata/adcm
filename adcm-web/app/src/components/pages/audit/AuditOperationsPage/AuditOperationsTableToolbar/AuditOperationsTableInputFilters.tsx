import type React from 'react';
import { useStore, useDispatch } from '@hooks';
import { setFilter } from '@store/adcm/audit/auditOperations/auditOperationsTableSlice';
import { SearchInput } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';
import s from './AuditOperationsTableInputFilters.module.scss';

const AuditOperationsTableInputFilters = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.auditOperationsTable.filter);

  const handleObjectNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ objectName: event.target.value }));
  };

  const handleUsernameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ username: event.target.value }));
  };

  return (
    <TableFilters>
      <SearchInput
        className={s.auditSelect}
        placeholder="Search object"
        value={filter.objectName || ''}
        variant="primary"
        onChange={handleObjectNameChange}
      />
      <SearchInput
        className={s.auditSelect}
        placeholder="Search username"
        value={filter.username || ''}
        variant="primary"
        onChange={handleUsernameChange}
      />
    </TableFilters>
  );
};

export default AuditOperationsTableInputFilters;
