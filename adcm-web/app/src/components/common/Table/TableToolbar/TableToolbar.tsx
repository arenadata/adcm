import s from './TableToolbar.module.scss';
import cn from 'classnames';

interface TableToolbarProps extends React.PropsWithChildren {
  direction?: 'column' | 'row';
  dataTest?: string;
}

const TableToolbar = ({ children, direction = 'row', dataTest = 'toolbar-container' }: TableToolbarProps) => (
  <div className={cn(s.tableToolbar, { [s.tableToolbar_column]: direction === 'column' })} data-test={dataTest}>
    {children}
  </div>
);

export default TableToolbar;
