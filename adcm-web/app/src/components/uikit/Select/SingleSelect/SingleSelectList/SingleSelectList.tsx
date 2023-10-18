import React, { useMemo } from 'react';
import { SelectOption } from '@uikit/Select/Select.types';
import s from './SingleSelectList.module.scss';
import cn from 'classnames';
import { useSingleSelectContext } from '../SingleSelectContext/SingleSelect.context';
import { ConditionalWrapper, Tooltip } from '@uikit';

const SingleSelectList = <T,>() => {
  const {
    //
    options: outerOptions,
    value: selectedValue,
    onChange,
    noneLabel,
    maxHeight,
    renderItem,
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
    <ul className={cn(s.singleSelectList, 'scroll')} style={{ maxHeight }}>
      {options.map(({ value, label, disabled, title }) => (
        <SingleSelectOptionsItem
          key={label.toString()}
          onSelect={() => {
            selectedValue !== value && onChange(value);
          }}
          isSelected={selectedValue === value}
          title={title}
          disabled={disabled}
        >
          {renderItem ? renderItem({ value, label, disabled, title }) : label}
        </SingleSelectOptionsItem>
      ))}
    </ul>
  );
};
export default SingleSelectList;

interface SingleSelectListItemProps {
  children: React.ReactNode;
  disabled?: boolean;
  title?: string;
  onSelect?: () => void;
  isSelected?: boolean;
}
const SingleSelectOptionsItem: React.FC<SingleSelectListItemProps> = ({
  onSelect,
  children,
  disabled,
  title,
  isSelected,
}) => {
  const handleClick = () => {
    if (disabled) return;
    onSelect?.();
  };
  const itemClass = cn(s.singleSelectListItem, {
    [s.singleSelectListItem_selected]: isSelected,
    [s.singleSelectListItem_disabled]: disabled,
  });

  return (
    <ConditionalWrapper Component={Tooltip} isWrap={!!title} label={title} placement={'bottom-start'}>
      <li className={itemClass} onClick={handleClick}>
        {children}
      </li>
    </ConditionalWrapper>
  );
};
