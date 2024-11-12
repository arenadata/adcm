import React, { useState, useEffect } from 'react';
import SearchInput from '@uikit/SearchInput/SearchInput';
import { getFilteredOptions } from './CommonSelectSearchFilter.utils';
import type { SelectOption } from '@uikit/Select/Select.types';

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
    onSearch?.(searchStr);
  };

  useEffect(() => {
    setOptions(getFilteredOptions(originalOptions, search));
  }, [originalOptions, search, setOptions]);

  return <SearchInput className={className} placeholder={searchPlaceholder} value={search} onChange={handleSearch} />;
};

export default CommonSelectSearchFilter;
