import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import JobsTableToolbar from './JobsTableToolbar/JobsTableToolbar';
import JobsTable from './JobsTable/JobsTable';
import JobsTableFooter from './JobsTableFooter/JobsTableFooter';
import { useRequestJobs } from './useRequestJobs';
import JobsDialogs from './Dialogs';
import { useDispatch } from '@hooks';
import { useEffect } from 'react';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';

const JobsPage = () => {
  useRequestJobs();

  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(setBreadcrumbs([]));
  }, [dispatch]);

  return (
    <TableContainer variant="easy">
      <JobsTableToolbar />
      <JobsTable />
      <JobsTableFooter />
      <JobsDialogs />
    </TableContainer>
  );
};

export default JobsPage;
