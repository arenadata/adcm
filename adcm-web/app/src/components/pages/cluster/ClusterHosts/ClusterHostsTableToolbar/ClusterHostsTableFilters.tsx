import React, { useMemo } from 'react';
import { useDispatch, useStore } from '@hooks';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';
import { Button, LabeledField, SearchInput, Select } from '@uikit';
import { resetFilter, resetSortParams, setFilter } from '@store/adcm/cluster/hosts/hostsTableSlice';

const ClusterHostsTableFilters = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.clusterHostsTable.filter);
  const hostProviders = useStore(({ adcm }) => adcm.clusterHostsTable.relatedData.hostProviders);

  const hostProviderOptions = useMemo(() => {
    return hostProviders.map(({ name }) => ({
      value: name,
      label: name,
    }));
  }, [hostProviders]);

  const handleResetClick = () => {
    dispatch(resetFilter());
    dispatch(resetSortParams());
  };

  const handleHostNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ name: event.target.value }));
  };

  const handleHostProviderChange = (value: string | null) => {
    dispatch(setFilter({ hostprovider: value ?? undefined }));
  };

  return (
    <TableFilters>
      <SearchInput
        placeholder="Search hostname"
        value={filter.name || ''}
        variant="primary"
        onChange={handleHostNameChange}
      />
      <LabeledField label="Hostprovider" direction="row">
        <Select
          maxHeight={200}
          placeholder="All"
          value={filter.hostprovider ?? null}
          onChange={handleHostProviderChange}
          options={hostProviderOptions}
          noneLabel="All"
        />
      </LabeledField>
      <Button variant="tertiary" iconLeft="g1-return" onClick={handleResetClick} />
    </TableFilters>
  );
};

export default ClusterHostsTableFilters;
