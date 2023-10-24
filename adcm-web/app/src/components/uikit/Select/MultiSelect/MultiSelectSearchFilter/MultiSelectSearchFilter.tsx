import React, { useState } from 'react';
import { useMultiSelectContext } from '../MultiSelectContext/MultiSelect.context';
import CommonSelectSearchFilter from '@uikit/Select/CommonSelect/CommonSelectSearchFilter/CommonSelectSearchFilter';
import s from './MultiSelectSearchFilter.module.scss';
import Button from '@uikit/Button/Button';

const MultiSelectSearchFilter: React.FC = <T,>() => {
  const {
    originalOptions,
    options: filteredOptions,
    setOptions,
    onChange,
    searchPlaceholder,
  } = useMultiSelectContext<T>();

  const [search, setSearch] = useState('');

  const isFilterDisabled = search.length === 0 || filteredOptions.length === 0;
  const handleSelectFiltered = () => {
    const allFilteredList = filteredOptions.map(({ value }) => value);
    onChange(allFilteredList);
  };

  return (
    <div className={s.multiSelectSearchFilter} data-test="search-filter">
      <CommonSelectSearchFilter
        originalOptions={originalOptions}
        setOptions={setOptions}
        searchPlaceholder={searchPlaceholder}
        className={s.multiSelectSearchFilter__select}
        onSearch={setSearch}
      />
      <Button disabled={isFilterDisabled} onClick={handleSelectFiltered}>
        Select filtered
      </Button>
    </div>
  );
};

export default MultiSelectSearchFilter;
