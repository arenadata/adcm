import React from 'react';
import { SingleSelectOptions } from '../../Select.types';
import SingleSelectList from '../SingleSelectList/SingleSelectList';
import s from './SingleSelectPanel.module.scss';
import SingleSelectSearchFilter from '../SingleSelectSearchFilter/SingleSelectSearchFilter';
import CommonSelectNoResult from '@uikit/Select/CommonSelect/CommonSelectNoResult/CommonSelectNoResult';
import { SingleSelectContextProvider } from '../SingleSelectContext/SingleSelectContextProvider';
import { useSingleSelectContext } from '../SingleSelectContext/SingleSelect.context';

export type SingleSelectPanelProps<T> = SingleSelectOptions<T>;

function SingleSelectPanel<T>(props: SingleSelectPanelProps<T>) {
  return (
    <div className={s.singleSelectPanel}>
      <SingleSelectContextProvider value={props}>
        <SingleSelectContent />
      </SingleSelectContextProvider>
    </div>
  );
}

export default SingleSelectPanel;

const SingleSelectContent = <T,>() => {
  const { isSearchable, options } = useSingleSelectContext<T>();
  const isShowOptions = options.length > 0;
  return (
    <>
      {isSearchable && (
        <div data-test="search-filter">
          <SingleSelectSearchFilter />
        </div>
      )}
      {isShowOptions ? <SingleSelectList /> : <CommonSelectNoResult />}
    </>
  );
};
