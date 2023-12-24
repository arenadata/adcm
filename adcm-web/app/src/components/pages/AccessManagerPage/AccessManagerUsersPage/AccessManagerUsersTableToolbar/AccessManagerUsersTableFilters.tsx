import React from 'react';
import { useStore, useDispatch } from '@hooks';
import { setFilter, resetFilter, resetSortParams } from '@store/adcm/users/usersTableSlice';
import { Button, LabeledField, SearchInput, Select } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';
import { AdcmUserStatus, AdcmUserType } from '@models/adcm';
import { getOptionsFromEnum } from '@uikit/Select/Select.utils';

const statusOptions = getOptionsFromEnum(AdcmUserStatus);
const typeOptions = getOptionsFromEnum(AdcmUserType);

const AccessManagerUsersTableFilters = () => {
  const dispatch = useDispatch();

  const { filter } = useStore((s) => s.adcm.usersTable);

  const handleUserNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ username: event.target.value }));
  };

  const handleStatusChange = (value: AdcmUserStatus | null) => {
    dispatch(setFilter({ status: value ?? undefined }));
  };

  const handleTypeChange = (value: AdcmUserType | null) => {
    dispatch(setFilter({ type: value ?? undefined }));
  };

  const handleResetFiltersClick = () => {
    dispatch(resetFilter());
    dispatch(resetSortParams());
  };

  return (
    <TableFilters>
      <SearchInput
        placeholder="Search user"
        value={filter.username || ''}
        variant="primary"
        onChange={handleUserNameChange}
      />
      <LabeledField label="Status" direction="row">
        <Select
          placeholder="All"
          value={filter.status ?? null}
          onChange={handleStatusChange}
          options={statusOptions}
          noneLabel="All"
        />
      </LabeledField>
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
      <Button variant="tertiary" iconLeft="g1-return" onClick={handleResetFiltersClick} />
    </TableFilters>
  );
};

export default AccessManagerUsersTableFilters;
