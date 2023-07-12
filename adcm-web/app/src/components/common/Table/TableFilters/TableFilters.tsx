import s from './TableFilters.module.scss';

const TableFilters = ({ children }: React.PropsWithChildren) => <div className={s.tableFilters}>{children}</div>;

export default TableFilters;
