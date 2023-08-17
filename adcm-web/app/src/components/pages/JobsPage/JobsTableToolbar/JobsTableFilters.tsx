import React from 'react';
import { useStore, useDispatch } from '@hooks';
import { setFilter, resetFilter, resetSortParams } from '@store/adcm/jobs/jobsTableSlice';
import { Button, LabeledField, SearchInput, Select } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';
import { AdcmJobStatus } from '@models/adcm';
import { getOptionsFromEnum } from '@uikit/Select/Select.utils';

const statusOptions = getOptionsFromEnum(AdcmJobStatus);

const JobsTableFilters = () => {
  const dispatch = useDispatch();

  const { filter } = useStore((s) => s.adcm.jobsTable);

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ name: event.target.value }));
  };

  const handleObjectChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ object: event.target.value }));
  };

  const handleStatusChange = (value: AdcmJobStatus | null) => {
    dispatch(setFilter({ status: value ?? undefined }));
  };

  const handleResetFiltersClick = () => {
    dispatch(resetFilter());
    dispatch(resetSortParams());
  };

  return (
    <TableFilters>
      <SearchInput placeholder="Search job" value={filter.name || ''} variant="primary" onChange={handleNameChange} />
      <SearchInput
        placeholder="Search object"
        value={filter.object || ''}
        variant="primary"
        onChange={handleObjectChange}
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
      <Button variant="secondary" iconLeft="g1-return" onClick={handleResetFiltersClick} />
    </TableFilters>
  );
};

export default JobsTableFilters;
