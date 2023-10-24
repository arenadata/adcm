import React, { useState } from 'react';
import SearchInput from '@uikit/SearchInput/SearchInput';
import { getFilteredOptions } from './CommonSelectSearchFilter.utils';
import { SelectOption } from '@uikit/Select/Select.types';

interface CommonSelectSearchFilterProps<T> {
  originalOptions: SelectOption<T>[];
  setOptions: (list: SelectOption<T>[]) => void;
  searchPlaceholder?: string;
  className?: string;
  onSearch?: (val: string) => void;
}

const CommonSelectSearchFilter = <T,>({
  originalOptions,
  setOptions,
  searchPlaceholder,
  className,
  onSearch,
}: CommonSelectSearchFilterProps<T>) => {
  const [search, setSearch] = useState('');
  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    const searchStr = e.target.value;
    setSearch(searchStr);
    setOptions(getFilteredOptions(originalOptions, searchStr));
    onSearch?.(searchStr);
  };

  return <SearchInput className={className} placeholder={searchPlaceholder} value={search} onChange={handleSearch} />;
};

export default CommonSelectSearchFilter;
