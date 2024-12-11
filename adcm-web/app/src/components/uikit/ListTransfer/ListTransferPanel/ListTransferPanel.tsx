import type { ChangeEvent } from 'react';
import type React from 'react';
import { useMemo, useState } from 'react';
import s from './ListTransferPanel.module.scss';
import { Button, Checkbox, SearchInput, Tooltip } from '@uikit';
import type { ListTransferItem, ListTransferItemOptions, ListTransferPanelOptions } from '../ListTransfer.types';
import cn from 'classnames';
import MarkerIcon from '@uikit/MarkerIcon/MarkerIcon';

interface ListTransferPanelProps extends ListTransferPanelOptions {
  list: ListTransferItem[];
  onAction: (keysList: ListTransferItem['key'][]) => void;
  ItemComponent: React.FC<ListTransferItemOptions>;
  className?: string;
  error?: string;
}

enum AllCheckboxState {
  CheckEnabled = 0,
  UncheckEnabled = 1,
  UncheckDisabled = 2,
}

const ListTransferPanel: React.FC<ListTransferPanelProps> = ({
  list,
  title,
  actionButtonLabel = 'Transfer selected',
  searchPlaceholder = 'Search',
  onAction,
  ItemComponent,
  className,
  error,
}) => {
  const [searchStr, setSearchStr] = useState('');
  const [selectedItemsKeys, setSelectedItemsKeys] = useState<Set<ListTransferItem['key']>>(new Set());

  const filteredItems = useMemo(() => {
    if (searchStr === '') return list;

    const lowSearchStr = searchStr.toLowerCase();
    return list.filter(({ label }) => label.toLowerCase().includes(lowSearchStr));
  }, [list, searchStr]);

  const notIncludedKeysList = useMemo(() => {
    return filteredItems.filter(({ isInclude }) => !isInclude).map(({ key }) => key);
  }, [filteredItems]);

  // for should not use included items and should disable "All filtered" checkbox
  const filteredSelectedState = useMemo<AllCheckboxState>(() => {
    // There are included items only - should disable and uncheck "All filtered" checkbox
    if (notIncludedKeysList.length === 0) return AllCheckboxState.UncheckDisabled;

    const isAllNotIncludesSelected = notIncludedKeysList.every((key) => selectedItemsKeys.has(key));

    // There are notIncluded items only - should enable and check "All filtered" checkbox
    if (isAllNotIncludesSelected) return AllCheckboxState.CheckEnabled;

    return AllCheckboxState.UncheckEnabled;
  }, [selectedItemsKeys, notIncludedKeysList]);

  const isSomeSelected = selectedItemsKeys.size > 0;

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => setSearchStr(e.target.value);

  const handleActionClick = () => {
    const keysList = [...selectedItemsKeys];
    setSelectedItemsKeys(new Set([]));
    onAction(keysList);
  };

  const handleAllSelectChange = (event: ChangeEvent<HTMLInputElement>) => {
    const isChecked = event.target.checked;
    setSelectedItemsKeys(new Set(isChecked ? notIncludedKeysList : []));
  };

  const handleSelect = (key: ListTransferItem['key'], isChecked: boolean) => {
    setSelectedItemsKeys((prev) => {
      if (isChecked) {
        prev.add(key);
      } else {
        prev.delete(key);
      }
      return new Set(prev);
    });
  };

  const handleReplace = (key: ListTransferItem['key']) => {
    selectedItemsKeys.delete(key);
    setSelectedItemsKeys(new Set(selectedItemsKeys));
    onAction([key]);
  };

  const isAllFilteredSelected = filteredSelectedState === AllCheckboxState.CheckEnabled;
  const isAllFilteredDisabled = filteredSelectedState === AllCheckboxState.UncheckDisabled;

  return (
    <div className={cn(s.listTransferPanel, className)} data-test="transfer-list-container">
      <div className={s.listTransferPanel__title}>
        <span>{title}</span>
        {!!error && (
          <Tooltip label={error} placement="top-start">
            <MarkerIcon type="alert" variant="square" />
          </Tooltip>
        )}
      </div>
      <div className={s.listTransferPanel__filters}>
        <SearchInput
          value={searchStr}
          onChange={handleSearchChange}
          className={s.listTransferPanel__search}
          placeholder={searchPlaceholder}
        />
        <Button variant="secondary" onClick={handleActionClick} disabled={!isSomeSelected}>
          {actionButtonLabel}
        </Button>
      </div>
      <div className={s.listTransferPanel__checkAll}>
        <Checkbox
          checked={isAllFilteredSelected}
          onChange={handleAllSelectChange}
          disabled={isAllFilteredDisabled}
          label="All filtered"
        />
      </div>
      <div className={cn(s.listTransferPanel__list, 'scroll')}>
        {filteredItems.map((item) => (
          <ItemComponent
            key={item.key}
            item={item}
            isSelected={selectedItemsKeys.has(item.key)}
            onReplace={handleReplace}
            onSelect={handleSelect}
          />
        ))}
      </div>
    </div>
  );
};
export default ListTransferPanel;
