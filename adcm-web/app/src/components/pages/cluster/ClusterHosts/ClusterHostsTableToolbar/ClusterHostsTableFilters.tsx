import type React from 'react';
import { useMemo } from 'react';
import { useDispatch, useStore } from '@hooks';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';
import { Button, LabeledField, SearchInput, Select } from '@uikit';
import { resetFilter, resetSortParams, setFilter } from '@store/adcm/cluster/hosts/hostsTableSlice';

const ClusterHostsTableFilters = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.clusterHostsTable.filter);
  const hostProviders = useStore(({ adcm }) => adcm.clusterHostsTable.relatedData.hostProviders);
  const hostComponents = useStore(({ adcm }) => adcm.clusterHostsTable.relatedData.hostComponents);

  const hostProviderOptions = useMemo(() => {
    return hostProviders.map(({ name }) => ({
      value: name,
      label: name,
    }));
  }, [hostProviders]);

  const hostComponentOptions = useMemo(() => {
    return hostComponents.map(({ id, displayName }) => ({
      value: id.toString(),
      label: displayName,
    }));
  }, [hostComponents]);

  const handleResetClick = () => {
    dispatch(resetFilter());
    dispatch(resetSortParams());
  };

  const handleHostNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ name: event.target.value }));
  };

  const handleHostProviderChange = (value: string | null) => {
    dispatch(setFilter({ hostproviderName: value ?? undefined }));
  };

  const handleHostComponentChange = (value: string | null) => {
    dispatch(setFilter({ componentId: value ?? undefined }));
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
          value={filter.hostproviderName ?? null}
          onChange={handleHostProviderChange}
          options={hostProviderOptions}
          noneLabel="All"
        />
      </LabeledField>
      <LabeledField label="Component" direction="row">
        <Select
          isSearchable={true}
          maxHeight={200}
          placeholder="Choose component"
          value={filter.componentId ?? null}
          onChange={handleHostComponentChange}
          options={hostComponentOptions}
          noneLabel="All"
        />
      </LabeledField>
      <Button variant="tertiary" iconLeft="g1-return" onClick={handleResetClick} />
    </TableFilters>
  );
};

export default ClusterHostsTableFilters;
