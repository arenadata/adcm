import React, { ChangeEvent } from 'react';
import { useMultiSelectContext } from '../MultiSelectContext/MultiSelect.context';
import Checkbox from '@uikit/Checkbox/Checkbox';
import s from './MultiSelectList.module.scss';
import cn from 'classnames';
import { ConditionalWrapper, Tooltip } from '@uikit';

const MultiSelectList = <T,>() => {
  const {
    //
    options,
    value: selectedValues,
    onChange,
    maxHeight,
  } = useMultiSelectContext<T>();

  const getHandleChange = (value: T) => (e: ChangeEvent<HTMLInputElement>) => {
    const valueIndex = selectedValues.indexOf(value);
    const newSelectedValues = [...selectedValues];

    if (e.target.checked && valueIndex === -1) {
      newSelectedValues.push(value);
    } else if (!e.target.checked && valueIndex > -1) {
      newSelectedValues.splice(valueIndex, 1);
    }

    onChange(newSelectedValues);
  };

  return (
    <ul className={cn(s.multiSelectList, 'scroll')} style={{ maxHeight }} data-test="options">
      {options.map(({ value, label, disabled, title }) => (
        <ConditionalWrapper
          key={label?.toString() + value}
          Component={Tooltip}
          isWrap={!!title}
          label={title}
          placement="bottom-start"
        >
          <li className={s.multiSelectList__item}>
            <Checkbox
              label={label}
              disabled={disabled}
              checked={selectedValues.includes(value)}
              onChange={getHandleChange(value)}
              className={s.multiSelectList__checkbox}
            />
          </li>
        </ConditionalWrapper>
      ))}
    </ul>
  );
};

export default MultiSelectList;
