import type React from 'react';
import { useMemo } from 'react';
import { useStore, useDispatch } from '@hooks';
import { setFilter, resetFilter, resetSortParams } from '@store/adcm/clusters/clustersTableSlice';
import { Button, LabeledField, SearchInput, Select } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';
import { AdcmClusterStatus } from '@models/adcm';
import { getOptionsFromEnum } from '@uikit/Select/Select.utils';

const statusOptions = getOptionsFromEnum(AdcmClusterStatus);

const ClustersTableFilters = () => {
  const dispatch = useDispatch();

  const {
    filter,
    relatedData: { prototypes },
  } = useStore((s) => s.adcm.clustersTable);

  const productsOptions = useMemo(() => {
    return prototypes.map(({ name, displayName }) => ({
      value: name,
      label: displayName,
    }));
  }, [prototypes]);

  const handleClusterNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ name: event.target.value }));
  };

  const handleResetFiltersClick = () => {
    dispatch(resetFilter());
    dispatch(resetSortParams());
  };

  const handleStatusChange = (value: AdcmClusterStatus | null) => {
    dispatch(setFilter({ status: value ?? undefined }));
  };

  const handleProductChange = (value: string | null) => {
    dispatch(setFilter({ prototypeName: value ?? undefined }));
  };

  return (
    <TableFilters>
      <SearchInput
        placeholder="Search cluster name"
        value={filter.name || ''}
        variant="primary"
        onChange={handleClusterNameChange}
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
      <LabeledField label="Product" direction="row">
        <Select
          isSearchable={true}
          maxHeight={200}
          placeholder="All"
          value={filter.prototypeName ?? null}
          onChange={handleProductChange}
          options={productsOptions}
          noneLabel="All"
        />
      </LabeledField>
      <Button variant="tertiary" iconLeft="g1-return" onClick={handleResetFiltersClick} />
    </TableFilters>
  );
};

export default ClustersTableFilters;
