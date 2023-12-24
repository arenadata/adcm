import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import AccessManagerUsersTableHeader from './AccessManagerUsersTableToolbar/AccessManagerUsersTableToolbar';
import AccessManagerUsersTable from './AccessManagerUsersTable/AccessManagerUsersTable';
import AccessManagerUsersTableFooter from './AccessManagerUsersTableFooter/AccessManagerUsersTableFooter';
import { useRequestAccessManagerUsers } from './useRequestAccessManagerUsers';
import AccessManagerUsersDialogs from './Dialogs';

const AccessManagerUsersPage = () => {
  useRequestAccessManagerUsers();

  return (
    <TableContainer variant="easy">
      <AccessManagerUsersTableHeader />
      <AccessManagerUsersTable />
      <AccessManagerUsersTableFooter />
      <AccessManagerUsersDialogs />
    </TableContainer>
  );
};

export default AccessManagerUsersPage;
