import { useMemo } from 'react';
import { useStore, useDispatch } from '@hooks';
import { setFilter, resetFilter, resetSortParams } from '@store/adcm/bundles/bundlesTableSlice';
import { Button, LabeledField, Select } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';

const BundlesTableFilters = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.bundlesTable.filter);
  const products = useStore(({ adcm }) => adcm.bundlesTable.relatedData.products);

  const productsOptions = useMemo(() => {
    return products.map(({ name, displayName }) => ({
      value: displayName,
      label: displayName || name,
    }));
  }, [products]);

  const handleResetClick = () => {
    dispatch(resetFilter());
    dispatch(resetSortParams());
  };
  const handleProductChange = (value: string | null) => {
    dispatch(setFilter({ displayName: value ?? undefined }));
  };

  return (
    <TableFilters>
      <LabeledField label="Product" direction="row">
        <Select
          isSearchable={true}
          maxHeight={200}
          placeholder="All"
          value={filter.displayName ?? null}
          onChange={handleProductChange}
          options={productsOptions}
          noneLabel="All"
        />
      </LabeledField>
      <Button variant="tertiary" iconLeft="g1-return" onClick={handleResetClick} />
    </TableFilters>
  );
};

export default BundlesTableFilters;
