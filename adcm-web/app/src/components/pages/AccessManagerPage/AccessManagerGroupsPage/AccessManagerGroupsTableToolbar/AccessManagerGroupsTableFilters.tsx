import React from 'react';
import { useStore, useDispatch } from '@hooks';
import { setFilter, resetFilter, resetSortParams } from '@store/adcm/groups/groupsTableSlice';
import { Button, LabeledField, SearchInput, Select } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';
import { AdcmGroupType } from '@models/adcm';
import { getOptionsFromEnum } from '@uikit/Select/Select.utils';

const typeOptions = getOptionsFromEnum(AdcmGroupType);

const AccessManagerGroupsTableFilters = () => {
  const dispatch = useDispatch();

  const { filter } = useStore((s) => s.adcm.groupsTable);

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ name: event.target.value }));
  };

  const handleTypeChange = (value: string | null) => {
    dispatch(setFilter({ type: value ?? undefined }));
  };

  const handleResetFiltersClick = () => {
    dispatch(resetFilter());
    dispatch(resetSortParams());
  };

  return (
    <TableFilters>
      <SearchInput placeholder="Search group" value={filter.name || ''} variant="primary" onChange={handleNameChange} />
      <LabeledField label="Type" direction="row">
        <Select
          isSearchable={true}
          maxHeight={200}
          placeholder="All"
          value={filter.type ?? null}
          onChange={handleTypeChange}
          options={typeOptions}
          noneLabel="All"
        />
      </LabeledField>
      <Button variant="secondary" iconLeft="g1-return" onClick={handleResetFiltersClick} />
    </TableFilters>
  );
};

export default AccessManagerGroupsTableFilters;
