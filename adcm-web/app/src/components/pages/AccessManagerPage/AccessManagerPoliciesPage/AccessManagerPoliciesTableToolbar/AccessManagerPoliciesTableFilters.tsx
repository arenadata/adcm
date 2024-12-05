import type React from 'react';
import { useStore, useDispatch } from '@hooks';
import { setFilter, resetFilter, resetSortParams } from '@store/adcm/policies/policiesTableSlice';
import { Button, SearchInput } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';

const AccessManagerPoliciesTableFilters: React.FC = () => {
  const dispatch = useDispatch();

  const { filter } = useStore((s) => s.adcm.policiesTable);

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ name: event.target.value }));
  };

  const handleResetFiltersClick = () => {
    dispatch(resetFilter());
    dispatch(resetSortParams());
  };
  return (
    <TableFilters>
      <SearchInput
        placeholder="Search policy"
        value={filter.name || ''}
        variant="primary"
        onChange={handleNameChange}
      />
      <Button variant="tertiary" iconLeft="g1-return" onClick={handleResetFiltersClick} />
    </TableFilters>
  );
};

export default AccessManagerPoliciesTableFilters;
