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
import { useParams } from 'react-router-dom';

const JobPage: React.FC = () => {
  useRequestJobPage();

  const dispatch = useDispatch();

  const task = useStore(({ adcm }) => adcm.jobs.task);

  const params = useParams();
  const logNamePartPath = params['*'] || 'stdout';

  useEffect(() => {
    if (task) {
      const jobBreadcrumbs = [{ href: '/jobs', label: 'Jobs' }, { label: task.displayName }];

      if (task.childJobs?.length === 1) {
        jobBreadcrumbs.push({ label: logNamePartPath });
      }

      dispatch(setBreadcrumbs(jobBreadcrumbs));
    }
  }, [task, logNamePartPath, dispatch]);

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
