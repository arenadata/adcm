import React from 'react';
import { useStore, useDispatch } from '@hooks';
import { setFilter } from '@store/adcm/host/hostTableSlice';
import { SearchInput } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';

const HostComponentsTableFilters: React.FC = () => {
  const dispatch = useDispatch();

  const { filter } = useStore((s) => s.adcm.hostTable);

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ name: event.target.value }));
  };

  return (
    <TableFilters>
      <SearchInput
        placeholder="Search component"
        value={filter.name || ''}
        variant="primary"
        onChange={handleNameChange}
      />
    </TableFilters>
  );
};

export default HostComponentsTableFilters;
