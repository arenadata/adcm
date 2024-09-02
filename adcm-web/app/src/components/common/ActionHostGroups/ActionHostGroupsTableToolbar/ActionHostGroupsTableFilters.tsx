import React from 'react';
import { Button, SearchInput } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';
import { AdcmActionHostGroupsFilter } from '@models/adcm';

export interface ActionHostGroupsTableFiltersProps {
  filter: AdcmActionHostGroupsFilter;
  onFilterChange: (changes: Partial<AdcmActionHostGroupsFilter>) => void;
  onFilterReset: () => void;
}

const ActionHostGroupsTableFilters = ({ filter, onFilterChange, onFilterReset }: ActionHostGroupsTableFiltersProps) => {
  const handleGroupNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ name: event.target.value });
  };

  const handleHostNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ hasHost: event.target.value });
  };

  return (
    <TableFilters>
      <SearchInput
        placeholder="Search group name"
        value={filter.name || ''}
        variant="primary"
        onChange={handleGroupNameChange}
      />
      <SearchInput
        placeholder="Search host name"
        value={filter.hasHost || ''}
        variant="primary"
        onChange={handleHostNameChange}
      />
      <Button variant="tertiary" iconLeft="g1-return" onClick={onFilterReset} />
    </TableFilters>
  );
};

export default ActionHostGroupsTableFilters;
