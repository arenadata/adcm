import AuditOperationsTableFilters from './AuditOperationsTableInputFilters';
import AuditOperationsTableNotInputFilters from './AuditOperationsTableNotInputFilters';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';

const AuditOperationsTableToolbar = () => (
  <TableToolbar direction="column">
    <AuditOperationsTableFilters />
    <AuditOperationsTableNotInputFilters />
  </TableToolbar>
);

export default AuditOperationsTableToolbar;
