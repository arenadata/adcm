import React, { useMemo } from 'react';
import CheckAll from '@uikit/CheckAll/CheckAll';
import { useMultiSelectContext } from '../MultiSelectContext/MultiSelect.context';

const MultiSelectFullCheckAll = <T,>() => {
  const { originalOptions, checkAllLabel, onChange, value: selectedValues } = useMultiSelectContext<T>();

  const allOptionsList = useMemo(() => {
    return originalOptions.map(({ value }) => value);
  }, [originalOptions]);

  return (
    <CheckAll allList={allOptionsList} selectedValues={selectedValues} onChange={onChange} label={checkAllLabel} />
  );
};

export default MultiSelectFullCheckAll;
