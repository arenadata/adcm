import { TableCell, Statusable, BaseStatus } from '@uikit';
import { Size } from '@uikit/types/size.types';
import s from './StatusableCell.module.scss';

export interface StatusableCellProps extends React.PropsWithChildren {
  status: BaseStatus;
  size?: Size;
  endAdornment?: React.ReactNode;
}

const StatusableCell = ({ children, status, size, endAdornment }: StatusableCellProps) => (
  <TableCell className={s.statusableCell}>
    <Statusable status={status} size={size}>
      {children}
    </Statusable>
    {endAdornment}
  </TableCell>
);

export default StatusableCell;
