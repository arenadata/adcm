import type React from 'react';
import { Tag, IconButton } from '@uikit';

export interface MappedHostProps {
  id: number;
  label: string;
  isDisabled?: boolean;
  deleteButtonTooltip?: React.ReactNode;
  onDeleteClick: (e: React.MouseEvent<HTMLButtonElement>) => void;
}

const MappedHost = ({ id, label, isDisabled = false, deleteButtonTooltip, onDeleteClick }: MappedHostProps) => (
  <Tag
    isDisabled={isDisabled}
    endAdornment={
      <IconButton
        //
        data-id={id}
        icon="g1-remove"
        variant="primary"
        size={20}
        onClick={onDeleteClick}
        title={deleteButtonTooltip ?? 'Remove'}
        disabled={isDisabled}
      />
    }
  >
    {label}
  </Tag>
);

export default MappedHost;
