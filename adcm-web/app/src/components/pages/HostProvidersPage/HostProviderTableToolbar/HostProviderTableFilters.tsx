import React, { useMemo } from 'react';
import { useStore, useDispatch } from '@hooks';
import { setFilter, resetFilter } from '@store/adcm/hostProviders/hostProvidersTableSlice';
import { Button, LabeledField, SearchInput, Select } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';

const HostProviderTableFilters = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.hostProvidersTable.filter);
  const prototypes = useStore(({ adcm }) => adcm.hostProvidersTable.relatedData.prototypes);

  const typeOptions = useMemo(
    () =>
      prototypes.map((prototype) => ({
        value: prototype.displayName,
        label: prototype.displayName,
      })),
    [prototypes],
  );

  const handleBundleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ name: event.target.value }));
  };

  const handleResetFiltersClick = () => {
    dispatch(resetFilter());
  };
  const handlePrototypeChange = (value: string | null) => {
    dispatch(setFilter({ prototypeDisplayName: value ?? undefined }));
  };

  return (
    <TableFilters>
      <SearchInput
        placeholder="Search provider"
        value={filter.name || ''}
        variant="primary"
        onChange={handleBundleNameChange}
      />
      <LabeledField label="Type" direction="row">
        <Select
          maxHeight={200}
          placeholder="All"
          value={filter.prototypeDisplayName ?? null}
          onChange={handlePrototypeChange}
          options={typeOptions}
          noneLabel="All"
        />
      </LabeledField>
      <Button variant="secondary" iconLeft="g1-return" onClick={handleResetFiltersClick} />
    </TableFilters>
  );
};

export default HostProviderTableFilters;
