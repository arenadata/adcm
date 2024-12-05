import { useRequestAuditOperations } from './useRequestAuditOperations';
import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import AuditOperationsTable from '@pages/audit/AuditOperationsPage/AuditOperationsTable/AuditOperationsTable';
import AuditOperationsTableToolbar from '@pages/audit/AuditOperationsPage/AuditOperationsTableToolbar/AuditOperationsTableToolbar';
import AuditOperationsTableFooter from '@pages/audit/AuditOperationsPage/AuditOperationsTableFooter/AuditOperationsTableFooter';

const AuditOperationsPage = () => {
  useRequestAuditOperations();

  return (
    <TableContainer variant="easy">
      <AuditOperationsTableToolbar />
      <AuditOperationsTable />
      <AuditOperationsTableFooter />
    </TableContainer>
  );
};

export default AuditOperationsPage;
