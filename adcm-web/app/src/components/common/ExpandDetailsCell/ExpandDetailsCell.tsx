import React from 'react';
import { Button, TableCell } from '@uikit';
import s from './ExpandDetailsCell.module.scss';

interface ExpandDetailsCellProps {
  isDisabled?: boolean;
  children: React.ReactNode;
  handleExpandRow: () => void;
}

const ExpandDetailsCell: React.FC<ExpandDetailsCellProps> = ({ isDisabled, handleExpandRow, children }) => {
  return (
    <TableCell>
      <div className={s.expandDetailsCell}>
        {children}
        <Button
          variant="secondary"
          disabled={isDisabled}
          iconLeft="dots"
          onClick={handleExpandRow}
          placeholder="Expand"
        />
      </div>
    </TableCell>
  );
};

export default ExpandDetailsCell;
