import type React from 'react';
import { useStore, useDispatch } from '@hooks';
import { setFilter, resetFilter, resetSortParams } from '@store/adcm/cluster/services/servicesTableSlice';
import { Button, SearchInput } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';

const ClusterServicesTableFilters = () => {
  const dispatch = useDispatch();
  const { filter } = useStore((s) => s.adcm.servicesTable);

  const handleClusterNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ displayName: event.target.value }));
  };

  const handleResetFiltersClick = () => {
    dispatch(resetFilter());
    dispatch(resetSortParams());
  };

  return (
    <TableFilters>
      <SearchInput
        placeholder="Search service"
        value={filter.displayName || ''}
        variant="primary"
        onChange={handleClusterNameChange}
      />
      <Button variant="tertiary" iconLeft="g1-return" onClick={handleResetFiltersClick} />
    </TableFilters>
  );
};

export default ClusterServicesTableFilters;
