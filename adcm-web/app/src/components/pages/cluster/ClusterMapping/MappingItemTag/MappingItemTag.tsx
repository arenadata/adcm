import React from 'react';
import { Tag, IconButton } from '@uikit';

export interface MappingItemTagProps {
  id: number;
  label: string;
  onDeleteClick: (e: React.MouseEvent<HTMLButtonElement>) => void;
  isDisabled?: boolean;
}

const MappingItemTag = ({ id, label, onDeleteClick, isDisabled = false }: MappingItemTagProps) => (
  <Tag
    isDisabled={isDisabled}
    endAdornment={
      <IconButton
        //
        data-id={id}
        icon="g1-remove"
        variant="secondary"
        size={20}
        onClick={onDeleteClick}
        title="Remove"
        disabled={isDisabled}
      />
    }
  >
    {label}
  </Tag>
);

export default MappingItemTag;
