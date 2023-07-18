import React, { useMemo } from 'react';
import { useStore, useDispatch } from '@hooks';
import { setFilter, resetFilter } from '@store/adcm/clusters/clustersTableSlice';
import { Button, SearchInput, Select } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';
import { AdcmClusterStatus } from '@models/adcm';
import { getOptionsFromEnum, getOptionsFromArray } from '@uikit/Select/Select.utils';

const statusOptions = getOptionsFromEnum(AdcmClusterStatus);

const ClustersTableFilters = () => {
  const dispatch = useDispatch();

  const {
    filter,
    relatedData: { prototypeNames },
  } = useStore((s) => s.adcm.clustersTable);

  const prototypeNamesOptions = useMemo(() => {
    return getOptionsFromArray(prototypeNames, (x) => x);
  }, [prototypeNames]);

  const handleClusterNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ clusterName: event.target.value }));
  };

  const handleResetFiltersClick = () => {
    dispatch(resetFilter());
  };

  const handleStatusChange = (value: AdcmClusterStatus | null) => {
    dispatch(setFilter({ clusterStatus: value ?? undefined }));
  };

  const handleProductChange = (value: string | null) => {
    dispatch(setFilter({ prototypeName: value ?? undefined }));
  };

  return (
    <TableFilters>
      <SearchInput
        placeholder="Search cluster name"
        value={filter.clusterName || ''}
        variant="primary"
        onChange={handleClusterNameChange}
      />
      <Select
        placeholder="Select cluster status"
        value={filter.clusterStatus ?? null}
        onChange={handleStatusChange}
        options={statusOptions}
        noneLabel="All"
      />
      <Select
        isSearchable={true}
        maxHeight={200}
        placeholder="Select product"
        value={filter.prototypeName ?? null}
        onChange={handleProductChange}
        options={prototypeNamesOptions}
        noneLabel="All"
      />
      <Button variant="secondary" iconLeft="g1-return" onClick={handleResetFiltersClick} />
    </TableFilters>
  );
};

export default ClustersTableFilters;
