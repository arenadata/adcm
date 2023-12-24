import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import JobPageTable from './JobPageTable/JobPageTable';
import { useRequestJobPage } from './useRequestJobPage';
import JobsSubPageStopHeader from './JobPageHeader/JobPageHeader';
import { useEffect } from 'react';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import JobPageChildJobsTable from './JobPageChildJobsTable/JobPageChildJobsTable';
import JobPageLog from './JobPageLog/JobPageLog';
import JobPageStopJobDialog from './Dialogs/JobPageStopJobDialog';

const JobPage: React.FC = () => {
  const { task, dispatch } = useRequestJobPage();

  useEffect(() => {
    if (task) {
      const jobBreadcrumbs = [{ href: '/jobs', label: 'Jobs' }, { label: task.displayName }];

      dispatch(setBreadcrumbs(jobBreadcrumbs));
    }
  }, [task, dispatch]);

  return (
    <>
      <JobsSubPageStopHeader />
      <TableContainer variant="easy">
        <JobPageTable />
      </TableContainer>
      {task.childJobs?.length === 1 && <JobPageLog id={task.childJobs[0].id} />}
      {task.childJobs && task.childJobs.length > 1 && (
        <TableContainer variant="easy">
          <JobPageChildJobsTable />
        </TableContainer>
      )}
      <JobPageStopJobDialog />
    </>
  );
};

export default JobPage;
