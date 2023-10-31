import React, { useMemo } from 'react';
import { useStore, useDispatch } from '@hooks';
import { setFilter, resetFilter, resetSortParams } from '@store/adcm/bundles/bundlesTableSlice';
import { Button, LabeledField, SearchInput, Select } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';

const BundlesTableFilters = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.bundlesTable.filter);
  const products = useStore(({ adcm }) => adcm.bundlesTable.relatedData.products);

  const productsOptions = useMemo(() => {
    return products.map(({ name, displayName }) => ({
      value: name,
      label: displayName || name,
    }));
  }, [products]);

  const handleBundleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ displayName: event.target.value }));
  };

  const handleResetClick = () => {
    dispatch(resetFilter());
    dispatch(resetSortParams());
  };
  const handleProductChange = (value: string | null) => {
    dispatch(setFilter({ product: value ?? undefined }));
  };

  return (
    <TableFilters>
      <SearchInput
        placeholder="Search bundle"
        value={filter.displayName || ''}
        variant="primary"
        onChange={handleBundleNameChange}
      />
      <LabeledField label="Product" direction="row">
        <Select
          isSearchable={true}
          maxHeight={200}
          placeholder="All"
          value={filter.product ?? null}
          onChange={handleProductChange}
          options={productsOptions}
          noneLabel="All"
        />
      </LabeledField>
      <Button variant="secondary" iconLeft="g1-return" onClick={handleResetClick} />
    </TableFilters>
  );
};

export default BundlesTableFilters;
