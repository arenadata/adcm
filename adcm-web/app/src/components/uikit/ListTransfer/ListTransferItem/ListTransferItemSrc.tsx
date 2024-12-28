import type { ChangeEvent } from 'react';
import type React from 'react';
import type { ListTransferItemOptions } from '@uikit/ListTransfer/ListTransfer.types';
import { Checkbox, IconButton, Tag } from '@uikit';
import s from './ListTransferItem.module.scss';

const ListTransferItemSrc: React.FC<ListTransferItemOptions> = ({
  item: { key, label, isInclude },
  onSelect,
  onReplace,
  isSelected = false,
}) => {
  if (isInclude) {
    return <div className={s.listTransferItemSrc_include}>{label}</div>;
  }

  const handleChecked = (event: ChangeEvent<HTMLInputElement>) => {
    onSelect(key, event.target.checked);
  };
  const handleInclude = () => {
    onReplace(key);
  };

  return (
    <Tag
      startAdornment={<Checkbox checked={isSelected} onChange={handleChecked} />}
      endAdornment={
        <IconButton
          //
          icon="g1-import"
          variant="secondary"
          size={20}
          onClick={handleInclude}
          title="Replace"
        />
      }
    >
      {label}
    </Tag>
  );
};
export default ListTransferItemSrc;
