import React, { useMemo } from 'react';
import { SelectOption } from '@uikit/Select/Select.types';
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

  return (
    <ul>
      {options.map(({ value, label, disabled }) => (
        <SingleSelectOptionsItem
          key={label.toString()}
          onSelect={() => {
            selectedValue !== value && onChange(value);
          }}
          isSelected={selectedValue === value}
          disabled={disabled}
        >
          {label}
        </SingleSelectOptionsItem>
      ))}
    </ul>
  );
};
export default SingleSelectList;

interface SingleSelectListItemProps {
  children: React.ReactNode;
  disabled?: boolean;
  onSelect?: () => void;
  isSelected?: boolean;
}
const SingleSelectOptionsItem: React.FC<SingleSelectListItemProps> = ({ onSelect, children, disabled, isSelected }) => {
  const handleClick = () => {
    if (disabled) return;
    onSelect?.();
  };
  const itemClass = cn(s.singleSelectListItem, {
    [s.singleSelectListItem_selected]: isSelected,
    [s.singleSelectListItem_disabled]: disabled,
  });

  return (
    <li className={itemClass} onClick={handleClick}>
      {children}
    </li>
  );
};
