import React from 'react';
import { useStore, useDispatch } from '@hooks';
import { setFilter, resetFilter, resetSortParams } from '@store/adcm/roles/rolesTableSlice';
import { Button, SearchInput } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';

const AccessManagerRolesTableFilters = () => {
  const dispatch = useDispatch();

  const { filter } = useStore((s) => s.adcm.rolesTable);

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ displayName: event.target.value }));
  };

  const handleResetFiltersClick = () => {
    dispatch(resetFilter());
    dispatch(resetSortParams());
  };

  return (
    <TableFilters>
      <SearchInput
        placeholder="Search role"
        value={filter.displayName || ''}
        variant="primary"
        onChange={handleNameChange}
      />
      <Button variant="secondary" iconLeft="g1-return" onClick={handleResetFiltersClick} />
    </TableFilters>
  );
};

export default AccessManagerRolesTableFilters;
