import React from 'react';
import { useStore, useDispatch } from '@hooks';
import { setFilter } from '@store/adcm/cluster/hosts/host/clusterHostTableSlice';
import { SearchInput } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';

const HostComponentsTableFilters: React.FC = () => {
  const dispatch = useDispatch();

  const { filter } = useStore((s) => s.adcm.clusterHostTable);

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
