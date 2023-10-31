import React, { useMemo } from 'react';
import Checkbox from '@uikit/Checkbox/Checkbox';

export interface CheckAllProps<T> {
  allList: T[];
  selectedValues: T[] | null;
  onChange: (value: T[]) => void;
  label?: string;
  className?: string;
}

export const CheckAll = <T,>({ label, allList, selectedValues, onChange, className }: CheckAllProps<T>) => {
  const isAllChecked = useMemo(() => {
    if (!selectedValues?.length) return false;

    return allList.length === selectedValues.length;
  }, [allList, selectedValues]);

  const handlerAllChanged = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange?.(event.target.checked ? allList.map((item) => item) : []);
  };

  return <Checkbox label={label} className={className} checked={isAllChecked} onChange={handlerAllChanged} />;
};

export default CheckAll;
