import s from './TableToolbar.module.scss';

const TableToolbar = ({ children }: React.PropsWithChildren) => <div className={s.tableToolbar}>{children}</div>;

export default TableToolbar;
