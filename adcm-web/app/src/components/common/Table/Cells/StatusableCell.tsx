import { TableCell, Statusable, BaseStatus } from '@uikit';
import { Size } from '@uikit/types/size.types';

export interface StatusableCellProps extends React.PropsWithChildren {
  status: BaseStatus;
  size?: Size;
}

const StatusableCell = ({ children, status, size }: StatusableCellProps) => (
  <TableCell>
    <Statusable status={status} size={size}>
      {children}
    </Statusable>
  </TableCell>
);

export default StatusableCell;
