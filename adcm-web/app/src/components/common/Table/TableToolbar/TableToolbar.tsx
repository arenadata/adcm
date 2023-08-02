import s from './TableToolbar.module.scss';
import cn from 'classnames';

interface TableToolbarProps extends React.PropsWithChildren {
  direction?: 'column' | 'row';
}

const TableToolbar = ({ children, direction = 'row' }: TableToolbarProps) => (
  <div className={cn(s.tableToolbar, { [s.tableToolbar_column]: direction === 'column' })}>{children}</div>
);

export default TableToolbar;
