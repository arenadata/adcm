import React, { useState } from 'react';
import SearchInput from '@uikit/SearchInput/SearchInput';
import { getFilteredOptions } from './SingleSelectSearchFilter.utils';
import s from './SingleSelectSearchFilter.module.scss';
import { useSingleSelectContext } from '../SingleSelectContext/SingleSelect.context';

const SingleSelectSearchFilter: React.FC = <T,>() => {
  const { originalOptions, setOptions, searchPlaceholder } = useSingleSelectContext<T>();

  const [search, setSearch] = useState('');
  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    const searchStr = e.target.value;
    setSearch(searchStr);
    setOptions(getFilteredOptions(originalOptions, searchStr));
  };

  return (
    <SearchInput
      className={s.singleSelectSearchFilter}
      placeholder={searchPlaceholder}
      value={search}
      onChange={handleSearch}
    />
  );
};
export default SingleSelectSearchFilter;
