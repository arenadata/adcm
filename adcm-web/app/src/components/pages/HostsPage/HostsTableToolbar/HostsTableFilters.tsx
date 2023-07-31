import React, { useMemo } from 'react';
import { useStore, useDispatch } from '@hooks';
import { Button, LabeledField, SearchInput, Select } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';
import { resetFilter, resetSortParams, setFilter } from '@store/adcm/hosts/hostsTableSlice';
import { getStatusLabel } from '@utils/humanizationUtils';

const HostsTableFilters = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.hostsTable.filter);
  const clusters = useStore(({ adcm }) => adcm.hostsTable.relatedData.clusters);
  const hostProviders = useStore(({ adcm }) => adcm.hostsTable.relatedData.hostProviders);

  const clusterOptions = useMemo(() => {
    return clusters.map(({ name }) => ({
      value: name,
      label: getStatusLabel(name),
    }));
  }, [clusters]);

  const hostProviderOptions = useMemo(() => {
    return hostProviders.map(({ name }) => ({
      value: name,
      label: getStatusLabel(name),
    }));
  }, [hostProviders]);

  const handleResetClick = () => {
    dispatch(resetFilter());
    dispatch(resetSortParams());
  };

  const handleHostNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ hostName: event.target.value }));
  };

  const handleHostProviderChange = (value: string | null) => {
    dispatch(setFilter({ hostProvider: value ?? undefined }));
  };

  const handleClusterChange = (value: string | null) => {
    dispatch(setFilter({ clusterName: value ?? undefined }));
  };

  return (
    <TableFilters>
      <SearchInput
        placeholder="Search hostname"
        value={filter.hostName || ''}
        variant="primary"
        onChange={handleHostNameChange}
      />
      <LabeledField label="Hostprovider" direction="row">
        <Select
          maxHeight={200}
          placeholder="All"
          value={filter.hostProvider ?? null}
          onChange={handleHostProviderChange}
          options={hostProviderOptions}
          noneLabel="All"
        />
      </LabeledField>
      <LabeledField label="Cluster" direction="row">
        <Select
          maxHeight={200}
          placeholder="All"
          value={filter.clusterName ?? null}
          onChange={handleClusterChange}
          options={clusterOptions}
          noneLabel="All"
        />
      </LabeledField>
      <Button variant="secondary" iconLeft="g1-return" onClick={handleResetClick} />
    </TableFilters>
  );
};

export default HostsTableFilters;
