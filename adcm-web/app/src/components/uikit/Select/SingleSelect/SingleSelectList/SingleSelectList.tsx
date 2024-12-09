import { useMemo } from 'react';
import type { SelectOption, DefaultSelectListItemProps } from '@uikit/Select/Select.types';
import s from './SingleSelectList.module.scss';
import cn from 'classnames';
import { useSingleSelectContext } from '../SingleSelectContext/SingleSelect.context';
import ConditionalWrapper from '@uikit/ConditionalWrapper/ConditionalWrapper';
import Tooltip from '@uikit/Tooltip/Tooltip';

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

  return (
    <ul className={cn(s.singleSelectList, 'scroll')} style={{ maxHeight }} data-test="options">
      {options.map((optionProps) => {
        const { value, label, disabled, ItemComponent = SingleSelectOptionsItem } = optionProps;
        const isSelected = selectedValue === value;

        const itemClass = cn(s.singleSelectListItem, {
          [s.singleSelectListItem_selected]: isSelected,
          [s.singleSelectListItem_disabled]: disabled,
        });

        return (
          <ItemComponent
            key={label.toString()}
            onSelect={() => {
              selectedValue !== value && onChange(value);
            }}
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

const SingleSelectOptionsItem = <T,>({ onSelect, option, className }: DefaultSelectListItemProps<T>) => {
  const { disabled, title, label } = option;
  const handleClick = () => {
    if (disabled) return;
    onSelect?.();
  };

  return (
    <ConditionalWrapper Component={Tooltip} isWrap={!!title} label={title} placement="bottom-start">
      <li className={className} onClick={handleClick}>
        {label}
      </li>
    </ConditionalWrapper>
  );
};
