import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import AccessManagerRolesTableToolbar from './AccessManagerRolesTableToolbar/AccessManagerRolesTableToolbar';
import AccessManagerRolesTable from './AccessManagerRolesTable/AccessManagerRolesTable';
import AccessManagerRolesTableFooter from './AccessManagerRolesTableFooter/AccessManagerRolesTableFooter';
import { useRequestAccessManagerRoles } from './useRequestAccessManagerRoles';
import AccessManagerRolesDialogs from './Dialogs';

const AccessManagerRolesPage = () => {
  useRequestAccessManagerRoles();

  return (
    <TableContainer variant="easy">
      <AccessManagerRolesTableToolbar />
      <AccessManagerRolesTable />
      <AccessManagerRolesTableFooter />
      <AccessManagerRolesDialogs />
    </TableContainer>
  );
};

export default AccessManagerRolesPage;
