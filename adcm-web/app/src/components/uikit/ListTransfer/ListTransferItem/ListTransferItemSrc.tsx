import type React from 'react';
import { Checkbox } from '@uikit';
import type { ListTransferItemOptions } from '@uikit/ListTransfer/ListTransfer.types';
import s from './ListTransferItem.module.scss';

const ListTransferItemSrc: React.FC<ListTransferItemOptions> = ({ item: { key, label }, onReplace }) => {
  return (
    <Checkbox
      className={s.listTransferItem}
      checked={false}
      onChange={() => onReplace(key)}
      label={label}
    />
  );
};
export default ListTransferItemSrc;
