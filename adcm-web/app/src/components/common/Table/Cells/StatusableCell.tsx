import { TableCell, Statusable, BaseStatus } from '@uikit';

export interface StatusableCellProps extends React.PropsWithChildren {
  status: BaseStatus;
}

const StatusableCell = ({ children, status }: StatusableCellProps) => (
  <TableCell>
    <Statusable status={status}>{children}</Statusable>
  </TableCell>
);

export default StatusableCell;
