import { Fragment, useCallback, useMemo } from 'react';
import type { SelectOption, DefaultSelectListItemProps } from '@uikit/Select/Select.types';
import SingleSelectListItem from './SingleSelectListItem/SingleSelectListItem';
import VirtualList from '@uikit/VirtualList/VirtualList';
import {
  DEFAULT_SELECT_MAX_HEIGHT,
  SELECT_ITEM_ESTIMATE_SIZE,
  SELECT_VIRTUAL_LIST_MIN_WIDTH,
  VIRTUALIZE_LIST_MIN_COUNT,
} from '@uikit/Select/Select.constants';
import s from './SingleSelectList.module.scss';
import cn from 'classnames';
import { useSingleSelectContext } from '../SingleSelectContext/SingleSelect.context';

const getOptionKey = <T,>(option: SelectOption<T>) => `${String(option.value)}:${option.label}`;

const SingleSelectList = <T,>() => {
  const {
    //
    options: outerOptions,
    value: selectedValue,
    onChange,
    noneLabel,
    maxHeight = DEFAULT_SELECT_MAX_HEIGHT,
    isVirtualized = false,
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

  const renderOption = useCallback(
    (optionProps: SelectOption<T>) => {
      const { value, disabled, ItemComponent = DefaultSingleSelectListItem } = optionProps;
      const isSelected = selectedValue === value;

      const itemClass = cn(s.singleSelectListItem, {
        [s.singleSelectListItem_selected]: isSelected,
        [s.singleSelectListItem_disabled]: disabled,
      });

      return (
        <ItemComponent onSelect={handleSelectItem} isSelected={isSelected} className={itemClass} option={optionProps} />
      );
    },
    [handleSelectItem, selectedValue],
  );

  if (isVirtualized && options.length > VIRTUALIZE_LIST_MIN_COUNT) {
    const listHeight = Math.min(
      maxHeight,
      Math.max(options.length * SELECT_ITEM_ESTIMATE_SIZE, SELECT_ITEM_ESTIMATE_SIZE),
    );

    return (
      <VirtualList
        items={options}
        renderItem={renderOption}
        getItemKey={getOptionKey}
        className={cn(s.singleSelectList, s.singleSelectList_virtual, 'scroll')}
        style={{ height: listHeight, width: '100%', minWidth: SELECT_VIRTUAL_LIST_MIN_WIDTH }}
        estimateSize={SELECT_ITEM_ESTIMATE_SIZE}
        measureItems={false}
        data-test="options"
      />
    );
  }

  return (
    <div className={cn(s.singleSelectList, 'scroll')} style={{ maxHeight }} data-test="options">
      {options.map((option) => (
        <Fragment key={getOptionKey(option)}>{renderOption(option)}</Fragment>
      ))}
    </div>
  );
};
export default SingleSelectList;

const DefaultSingleSelectListItem = <T,>(props: DefaultSelectListItemProps<T>) => {
  const { label } = props.option;

  return (
    <SingleSelectListItem {...props}>
      <span>{label}</span>
    </SingleSelectListItem>
  );
};
