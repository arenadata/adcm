import { useMemo, useCallback } from 'react';
import { useMultiSelectContext } from '../MultiSelectContext/MultiSelect.context';
import Checkbox from '@uikit/Checkbox/Checkbox';
import MultiSelectListItem from './MultiSelectListItem/MultiSelectListItem';
import type { DefaultSelectListItemProps } from '@uikit/Select/Select.types';
import s from './MultiSelectList.module.scss';
import cn from 'classnames';

const MultiSelectList = <T,>() => {
  const {
    //
    options,
    value: selectedValues,
    onChange,
    maxHeight,
  } = useMultiSelectContext<T>();

  const selectedValuesSet = useMemo(() => new Set(selectedValues), [selectedValues]);

  const handleSelectItem = useCallback(
    (value: T | null) => {
      if (value === null) {
        return;
      }

      const changedSet = new Set(selectedValuesSet);

      if (selectedValuesSet.has(value)) {
        changedSet.delete(value);
      } else {
        changedSet.add(value);
      }

      onChange([...changedSet]);
    },
    [selectedValuesSet, onChange],
  );

  return (
    <ul className={cn(s.multiSelectList, 'scroll')} style={{ maxHeight }} data-test="options">
      {options.map((optionProps) => {
        const { value, label, ItemComponent = DefaultMultiSelectListItem } = optionProps;
        const isSelected = selectedValuesSet.has(value);
        return (
          <ItemComponent
            key={`${label}${value}`}
            onSelect={handleSelectItem}
            isSelected={isSelected}
            option={optionProps}
          />
        );
      })}
    </ul>
  );
};

export default MultiSelectList;

const DefaultMultiSelectListItem = <T,>(props: DefaultSelectListItemProps<T>) => {
  const { disabled, label, value } = props.option;

  const handleChange = () => {
    props.onSelect?.(value);
  };

  return (
    <MultiSelectListItem {...props}>
      <Checkbox label={label} disabled={disabled} checked={props.isSelected} onChange={handleChange} />
    </MultiSelectListItem>
  );
};
