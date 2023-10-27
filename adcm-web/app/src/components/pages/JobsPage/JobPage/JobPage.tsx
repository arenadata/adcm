import TableContainer from '@commonComponents/Table/TableContainer/TableContainer';
import JobPageTable from './JobPageTable/JobPageTable';
import { useRequestJobPage } from './useRequestJobPage';
import JobsSubPageStopHeader from './JobPageHeader/JobPageHeader';
import { useDispatch, useStore } from '@hooks';
import { useEffect } from 'react';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import JobPageChildJobsTable from './JobPageChildJobsTable/JobPageChildJobsTable';
import JobPageLog from './JobPageLog/JobPageLog';
import JobPageStopJobDialog from './Dialogs/JobPageStopJobDialog';

const JobPage: React.FC = () => {
  useRequestJobPage();

  const dispatch = useDispatch();
  const task = useStore(({ adcm }) => adcm.jobs.task);

  useEffect(() => {
    if (task) {
      dispatch(setBreadcrumbs([{ href: '/jobs', label: 'Jobs' }, { label: task.displayName }]));
    }
  }, [task, dispatch]);

  return (
    <>
      <JobsSubPageStopHeader />
      <TableContainer variant="easy">
        <JobPageTable />
      </TableContainer>
      {task.childJobs?.length === 1 && <JobPageLog id={task.childJobs?.[0]?.id} />}
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
