import React from 'react';
import { Button, TableCell } from '@uikit';
import s from './ExpandDetailsCell.module.scss';

interface ExpandDetailsCellProps {
  children: React.ReactNode;
  handleExpandRow: () => void;
}

const ExpandDetailsCell: React.FC<ExpandDetailsCellProps> = ({ handleExpandRow, children }) => {
  return (
    <TableCell>
      <div className={s.expandDetailsCell}>
        {children}
        <Button variant="secondary" iconLeft="dots" onClick={handleExpandRow} placeholder="Expand" />
      </div>
    </TableCell>
  );
};

export default ExpandDetailsCell;
