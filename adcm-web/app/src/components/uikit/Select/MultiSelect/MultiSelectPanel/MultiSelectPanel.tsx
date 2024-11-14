import React from 'react';
import { MultiSelectContextProvider } from '../MultiSelectContext/MultiSelectContextProvider';
import CommonSelectNoResult from '@uikit/Select/CommonSelect/CommonSelectNoResult/CommonSelectNoResult';
import type { MultiSelectOptions } from '@uikit/Select/Select.types';
import { useMultiSelectContext } from '../MultiSelectContext/MultiSelect.context';
import MultiSelectList from '../MultiSelectList/MultiSelectList';
import MultiSelectSearchFilter from '../MultiSelectSearchFilter/MultiSelectSearchFilter';

import s from './MultiSelectPanel.module.scss';
import MultiSelectFullCheckAll from '@uikit/Select/MultiSelect/MultiSelectFullCheckAll/MultiSelectFullCheckAll';
import cn from 'classnames';

const MultiSelectContent = <T,>() => {
  const { isSearchable, options, checkAllLabel, compactMode } = useMultiSelectContext<T>();
  const isShowOptions = options.length > 0;
  const hasCheckAll = !!checkAllLabel;
  return (
    <>
      {hasCheckAll && (
        <div
          className={cn(s.multiSelectPanel__section, {
            [s.multiSelectPanel__section_compactMode]: compactMode,
          })}
          data-test="check-all"
        >
          <MultiSelectFullCheckAll />
        </div>
      )}
      <div
        className={cn(s.multiSelectPanel__section, {
          [s.multiSelectPanel__section_compactMode]: compactMode,
        })}
      >
        {isSearchable && <MultiSelectSearchFilter />}
        <div data-test="options-container">{isShowOptions ? <MultiSelectList /> : <CommonSelectNoResult />}</div>
      </div>
    </>
  );
};

const MultiSelectPanel = <T,>(props: MultiSelectOptions<T>) => {
  return (
    <div className={s.multiSelectPanel}>
      <MultiSelectContextProvider value={props}>
        <MultiSelectContent />
      </MultiSelectContextProvider>
    </div>
  );
};

export default MultiSelectPanel;
