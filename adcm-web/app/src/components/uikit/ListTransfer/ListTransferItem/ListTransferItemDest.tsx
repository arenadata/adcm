import type { ChangeEvent } from 'react';
import React from 'react';
import { Checkbox, IconButton, Tag } from '@uikit';
import type { ListTransferItemOptions } from '@uikit/ListTransfer/ListTransfer.types';

const ListTransferItemDest: React.FC<ListTransferItemOptions> = ({
  item: { key, label },
  onSelect,
  onReplace,
  isSelected = false,
}) => {
  const handleChecked = (event: ChangeEvent<HTMLInputElement>) => {
    onSelect(key, event.target.checked);
  };
  const handleRemove = () => {
    onReplace(key);
  };

  return (
    <Tag
      startAdornment={<Checkbox checked={isSelected} onChange={handleChecked} />}
      endAdornment={
        <IconButton
          //
          icon="g1-remove"
          variant="secondary"
          size={20}
          onClick={handleRemove}
          title="Remove"
        />
      }
    >
      {label}
    </Tag>
  );
};
export default ListTransferItemDest;
