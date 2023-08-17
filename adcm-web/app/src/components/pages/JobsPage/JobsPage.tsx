import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import JobsTableToolbar from './JobsTableToolbar/JobsTableToolbar';
import JobsTable from './JobsTable/JobsTable';
import JobsTableFooter from './JobsTableFooter/JobsTableFooter';
import { useRequestJobs } from './useRequestJobs';
import JobsDialogs from './Dialogs';

const AccessManagerUsersPage = () => {
  useRequestJobs();

  return (
    <TableContainer variant="easy">
      <JobsTableToolbar />
      <JobsTable />
      <JobsTableFooter />
      <JobsDialogs />
    </TableContainer>
  );
};

export default AccessManagerUsersPage;
