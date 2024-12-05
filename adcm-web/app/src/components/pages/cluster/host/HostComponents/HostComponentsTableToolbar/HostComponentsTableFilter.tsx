import type React from 'react';
import { useStore, useDispatch } from '@hooks';
import { setFilter } from '@store/adcm/hostComponents/hostComponentsTableSlice';
import { SearchInput } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';

const HostComponentsTableFilters: React.FC = () => {
  const dispatch = useDispatch();

  const filter = useStore((s) => s.adcm.hostComponentsTable.filter);

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ displayName: event.target.value }));
  };

  return (
    <TableFilters>
      <SearchInput
        placeholder="Search component"
        value={filter.displayName || ''}
        variant="primary"
        onChange={handleNameChange}
      />
    </TableFilters>
  );
};

export default HostComponentsTableFilters;
