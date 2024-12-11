import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import AuditLoginsTableToolbar from '@pages/audit/AuditLoginsPage/AuditLoginsTableToolbar/AuditLoginsTableToolbar';
import AuditLoginsTable from '@pages/audit/AuditLoginsPage/AuditLoginsTable/AuditLoginsTable';
import AuditLoginsTableFooter from '@pages/audit/AuditLoginsPage/AuditLoginsTableFooter/AuditLoginsTableFooter';
import { useRequestAuditLogins } from '@pages/audit/AuditLoginsPage/useRequestAuditLogins';

const AuditLoginsPages = () => {
  useRequestAuditLogins();

  return (
    <TableContainer variant="easy">
      <AuditLoginsTableToolbar />
      <AuditLoginsTable />
      <AuditLoginsTableFooter />
    </TableContainer>
  );
};

export default AuditLoginsPages;
