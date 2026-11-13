import type { ChangeEvent } from 'react';
import type React from 'react';
import { useMemo, useState } from 'react';
import s from './ListTransferPanel.module.scss';
import { Button, SearchInput, Tooltip } from '@uikit';
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

const ListTransferPanel: React.FC<ListTransferPanelProps> = ({
  list,
  title,
  actionButtonLabel = 'Select filtered',
  searchPlaceholder = 'Search',
  onAction,
  ItemComponent,
  className,
  error,
}) => {
  const [searchStr, setSearchStr] = useState('');

  const filteredItems = useMemo(() => {
    if (searchStr === '') return list;

    const lowerSearch = searchStr.toLowerCase();
    return list.filter(({ label }) => label.toLowerCase().includes(lowerSearch));
  }, [list, searchStr]);

  const handleSearchChange = (event: ChangeEvent<HTMLInputElement>) => setSearchStr(event.target.value);

  const handleActionClick = () => {
    onAction(filteredItems.map(({ key }) => key));
  };

  const handleReplace = (key: ListTransferItem['key']) => {
    onAction([key]);
  };

  return (
    <div className={cn(s.listTransferPanel, className)} data-test="transfer-list-container">
      <div className={s.listTransferPanel__title}>
        <span className={s.listTransferPanel__titleText}>{title}</span>
        <span className={s.listTransferPanel__badge}>{list.length}</span>
        {!!error && (
          <Tooltip label={error} placement="top-start">
            <MarkerIcon type="alert" variant="square" />
          </Tooltip>
        )}
      </div>
      <div className={s.listTransferPanel__divider} />
      <div className={s.listTransferPanel__filters}>
        <span className={s.listTransferPanel__filterLabel}>Filtered by</span>
        <SearchInput
          value={searchStr}
          onChange={handleSearchChange}
          className={s.listTransferPanel__search}
          placeholder={searchPlaceholder}
        />
        <span className={s.listTransferPanel__counter}>
          {filteredItems.length} /{list.length}
        </span>
      </div>
      <Button
        variant="secondary"
        className={s.listTransferPanel__actionButton}
        onClick={handleActionClick}
        disabled={filteredItems.length === 0}
      >
        {actionButtonLabel} ({filteredItems.length})
      </Button>
      <div className={cn(s.listTransferPanel__list, 'scroll')}>
        {filteredItems.map((item) => (
          <ItemComponent key={item.key} item={item} onReplace={handleReplace} />
        ))}
      </div>
    </div>
  );
};
export default ListTransferPanel;
