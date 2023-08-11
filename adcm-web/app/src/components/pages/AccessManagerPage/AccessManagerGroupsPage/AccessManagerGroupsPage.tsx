import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import AccessManagerGroupsTable from './AccessManagerGroupsTable/AccessManagerGroupsTable';
import { useRequestAccessManagerGroups } from './useRequestAccessManagerGroups';
import AccessManagerGroupsDialogs from './Dialogs';
import AccessManagerGroupsTableToolbar from './AccessManagerGroupsTableToolbar/AccessManagerGroupsTableToolbar';
import AccessManagerGroupsTableFooter from './AccessManagerGroupsTableFooter/AccessManagerGroupsTableFooter';

const AccessManagerGroupsPage = () => {
  useRequestAccessManagerGroups();

  return (
    <TableContainer variant="easy">
      <AccessManagerGroupsTableToolbar />
      <AccessManagerGroupsTable />
      <AccessManagerGroupsTableFooter />
      <AccessManagerGroupsDialogs />
    </TableContainer>
  );
};

export default AccessManagerGroupsPage;
