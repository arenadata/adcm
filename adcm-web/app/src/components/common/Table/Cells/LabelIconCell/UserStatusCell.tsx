import React from 'react';
import s from './UserStatusCell.module.scss';
import { MarkerIcon, TableCell, Tooltip } from '@uikit';
import { AdcmUser, AdcmUserStatus } from '@models/adcm';
import cn from 'classnames';

interface UserStatusCellProps extends React.HTMLAttributes<HTMLDivElement> {
  user: AdcmUser;
  className?: string;
}

const UserStatusCell: React.FC<UserStatusCellProps> = ({ user, className }) => {
  return (
    <TableCell className={cn(s.cell, className)}>
      {user.status}
      {user.status === AdcmUserStatus.Blocked && (
        <Tooltip label={user.blockingReason} placement="right" closeDelay={100}>
          <MarkerIcon type="info" variant="square" />
        </Tooltip>
      )}
    </TableCell>
  );
};

export default UserStatusCell;
