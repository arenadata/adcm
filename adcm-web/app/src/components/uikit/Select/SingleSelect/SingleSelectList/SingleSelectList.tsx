import { useCallback, useMemo } from 'react';
import type { SelectOption, DefaultSelectListItemProps } from '@uikit/Select/Select.types';
import SingleSelectListItem from './SingleSelectListItem/SingleSelectListItem';
import s from './SingleSelectList.module.scss';
import cn from 'classnames';
import { useSingleSelectContext } from '../SingleSelectContext/SingleSelect.context';

const SingleSelectList = <T,>() => {
  const {
    //
    options: outerOptions,
    value: selectedValue,
    onChange,
    noneLabel,
    maxHeight,
  } = useSingleSelectContext<T>();

  const options = useMemo(() => {
    if (!noneLabel) {
      return outerOptions;
    }

    return [
      {
        value: null,
        label: noneLabel,
        disabled: false,
      } as SelectOption<T>,
      ...outerOptions,
    ];
  }, [noneLabel, outerOptions]);

  const handleSelectItem = useCallback(
    (value: T | null) => {
      selectedValue !== value && onChange(value);
    },
    [selectedValue, onChange],
  );

  return (
    <ul className={cn(s.singleSelectList, 'scroll')} style={{ maxHeight }} data-test="options">
      {options.map((optionProps) => {
        const { value, label, disabled, ItemComponent = DefaulSingleSelectListItem } = optionProps;
        const isSelected = selectedValue === value;

        const itemClass = cn(s.singleSelectListItem, {
          [s.singleSelectListItem_selected]: isSelected,
          [s.singleSelectListItem_disabled]: disabled,
        });

        return (
          <ItemComponent
            key={label.toString()}
            onSelect={handleSelectItem}
            isSelected={isSelected}
            className={itemClass}
            option={optionProps}
          />
        );
      })}
    </ul>
  );
};
export default SingleSelectList;

const DefaulSingleSelectListItem = <T,>(props: DefaultSelectListItemProps<T>) => {
  const { label } = props.option;

  return (
    <SingleSelectListItem {...props}>
      <span>{label}</span>
    </SingleSelectListItem>
  );
};
