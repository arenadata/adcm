import React from 'react';
import s from './SingleSelectSearchFilter.module.scss';
import { useSingleSelectContext } from '../SingleSelectContext/SingleSelect.context';
import CommonSelectSearchFilter from '@uikit/Select/CommonSelect/CommonSelectSearchFilter/CommonSelectSearchFilter';

const SingleSelectSearchFilter: React.FC = <T,>() => {
  const { originalOptions, setOptions, searchPlaceholder } = useSingleSelectContext<T>();

  return (
    <CommonSelectSearchFilter
      originalOptions={originalOptions}
      setOptions={setOptions}
      searchPlaceholder={searchPlaceholder}
      className={s.singleSelectSearchFilter}
    />
  );
};
export default SingleSelectSearchFilter;
