import React, { useEffect, useState } from 'react';
import { CheckAll, Checkbox } from '@uikit';
import { useStore } from '@hooks';
import s from './AccessManagerRolesTableProducts.module.scss';

interface AccessManagerRolesTableProductsProps {
  onSelect: (value: string[]) => void;
}

const AccessManagerRolesTableProducts = ({ onSelect }: AccessManagerRolesTableProductsProps) => {
  const products = useStore((s) => s.adcm.roles.relatedData.categories);

  const [productsSelected, setProductsSelected] = useState(products);

  useEffect(() => {
    onSelect(productsSelected);
  }, [onSelect, productsSelected]);

  const getHandlerProductsFilter = (name: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setProductsSelected(
      event.target.checked ? [...productsSelected, name] : productsSelected.filter((p) => p !== name),
    );
  };

  const handleCheckAllClick = (value: string[]) => {
    setProductsSelected(value);
  };

  return (
    <>
      {products.length > 0 && (
        <div className={s.content__checkboxes}>
          <CheckAll
            allList={products}
            selectedValues={productsSelected}
            onChange={handleCheckAllClick}
            label="All products"
          />
          {products.map((p, i) => (
            <Checkbox key={i} label={p} checked={productsSelected.includes(p)} onChange={getHandlerProductsFilter(p)} />
          ))}
        </div>
      )}
    </>
  );
};

export default AccessManagerRolesTableProducts;
