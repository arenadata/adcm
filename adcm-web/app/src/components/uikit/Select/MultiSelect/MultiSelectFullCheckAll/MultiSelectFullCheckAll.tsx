import { useCallback, useMemo } from 'react';
import CheckAll from '@uikit/CheckAll/CheckAll';
import { useMultiSelectContext } from '../MultiSelectContext/MultiSelect.context';

const MultiSelectFullCheckAll = <T,>() => {
  const { originalOptions, checkAllLabel, onChange, value: selectedValues } = useMultiSelectContext<T>();

  const allAllowOptionsList = useMemo(() => {
    return originalOptions.filter(({ disabled }) => !disabled).map(({ value }) => value);
  }, [originalOptions]);

  const selectedDisabledOptions = useMemo(() => {
    return originalOptions
      .filter(({ disabled, value }) => disabled && selectedValues.includes(value))
      .map(({ value }) => value);
  }, [originalOptions, selectedValues]);

  const checkedSelectedValue = useMemo(
    () => selectedValues?.filter((val) => allAllowOptionsList.includes(val)),
    [selectedValues, allAllowOptionsList],
  );

  const handleChange = useCallback(
    (allowSelectedValues: T[]) => {
      const resultSelectedValues = new Set(allowSelectedValues.concat(selectedDisabledOptions));
      onChange([...resultSelectedValues]);
    },
    [selectedDisabledOptions, onChange],
  );

  const isDisabledCheckAll = allAllowOptionsList.length === 0;

  return (
    <CheckAll
      allList={allAllowOptionsList}
      selectedValues={checkedSelectedValue}
      onChange={handleChange}
      label={checkAllLabel}
      disabled={isDisabledCheckAll}
    />
  );
};

export default MultiSelectFullCheckAll;
