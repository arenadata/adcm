import type React from 'react';
import { useMemo } from 'react';
import s from './ListTransfer.module.scss';
import ListTransferPanel from './ListTransferPanel/ListTransferPanel';
import type { ListTransferItem, ListTransferPanelOptions } from './ListTransfer.types';
import ListTransferItemSrc from './ListTransferItem/ListTransferItemSrc';
import ListTransferItemDest from './ListTransferItem/ListTransferItemDest';
import cn from 'classnames';

interface ListTransferProps {
  srcOptions?: Partial<ListTransferPanelOptions>;
  destOptions?: Partial<ListTransferPanelOptions>;
  srcList: ListTransferItem[];
  destKeys: Set<ListTransferItem['key']>;
  onChangeDest: (keys: Set<ListTransferItem['key']>) => void;
  srcError?: string;
  destError?: string;
  className?: string;
}

const ListTransfer: React.FC<ListTransferProps> = ({
  srcList: incomingList,
  destKeys,
  onChangeDest,
  srcOptions,
  destOptions,
  srcError,
  destError,
  className,
}) => {
  const srcList = useMemo(() => {
    return incomingList.map((item) => {
      const newItem = { ...item };
      newItem.isInclude = destKeys.has(item.key);
      return newItem;
    });
  }, [incomingList, destKeys]);

  const destList = useMemo(() => {
    return incomingList.filter((item) => destKeys.has(item.key));
  }, [incomingList, destKeys]);

  const handleAppendToDest = (list: ListTransferItem['key'][]) => {
    if (list.length > 0) {
      const fullDestKeys = new Set(destKeys);
      list.forEach((key) => {
        fullDestKeys.add(key);
      });
      onChangeDest(fullDestKeys);
    }
  };

  const handleRemoveFromDest = (list: ListTransferItem['key'][]) => {
    if (list.length > 0) {
      const fullDestKeys = new Set(destKeys);
      list.forEach((key) => {
        fullDestKeys.delete(key);
      });
      onChangeDest(fullDestKeys);
    }
  };

  return (
    <div className={cn(s.listTransfer, className)}>
      <ListTransferPanel
        title="Primary"
        {...srcOptions}
        list={srcList}
        onAction={handleAppendToDest}
        ItemComponent={ListTransferItemSrc}
        className={s.listTransfer__leftPanel}
        error={srcError}
      />
      <ListTransferPanel
        title="Secondary"
        {...destOptions}
        list={destList}
        onAction={handleRemoveFromDest}
        ItemComponent={ListTransferItemDest}
        className={s.listTransfer__rightPanel}
        error={destError}
      />
    </div>
  );
};
export default ListTransfer;
