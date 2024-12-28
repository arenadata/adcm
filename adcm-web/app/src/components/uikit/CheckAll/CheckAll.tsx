import Checkbox from '@uikit/Checkbox/Checkbox';
import type React from 'react';
import { useMemo } from 'react';

export interface CheckAllProps<T> {
  allList: T[];
  selectedValues: T[] | null;
  onChange: (value: T[]) => void;
  label?: string;
  className?: string;
  disabled?: boolean;
}

export const CheckAll = <T,>({ label, allList, selectedValues, onChange, className, disabled }: CheckAllProps<T>) => {
  const isAllChecked = useMemo(() => {
    if (!selectedValues?.length) return false;

    return allList.length === selectedValues.length;
  }, [allList, selectedValues]);

  const handlerAllChanged = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange?.(event.target.checked ? allList.map((item) => item) : []);
  };

  return (
    <Checkbox
      label={label}
      className={className}
      checked={isAllChecked}
      onChange={handlerAllChanged}
      disabled={disabled}
    />
  );
};

export default CheckAll;
