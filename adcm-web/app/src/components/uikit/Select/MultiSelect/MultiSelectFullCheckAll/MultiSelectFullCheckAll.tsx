import { useMemo } from 'react';
import CheckAll from '@uikit/CheckAll/CheckAll';
import { useMultiSelectContext } from '../MultiSelectContext/MultiSelect.context';

const MultiSelectFullCheckAll = <T,>() => {
  const { originalOptions, checkAllLabel, onChange, value: selectedValues } = useMultiSelectContext<T>();

  const allOptionsList = useMemo(() => {
    return originalOptions.map(({ value }) => value);
  }, [originalOptions]);

  const isDisabledCheckAll = useMemo(() => {
    return originalOptions.every(({ disabled }) => disabled);
  }, [originalOptions]);

  return (
    <CheckAll
      allList={allOptionsList}
      selectedValues={selectedValues}
      onChange={onChange}
      label={checkAllLabel}
      disabled={isDisabledCheckAll}
    />
  );
};

export default MultiSelectFullCheckAll;
