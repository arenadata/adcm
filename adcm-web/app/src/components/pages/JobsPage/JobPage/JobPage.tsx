import { useEffect, useRef } from 'react';
import { useDispatch, useStore } from '@hooks';
import JobOverviewTable from './JobOverviewTable/JobOverviewTable';
import JobsPageHeader from './JobPageHeader/JobPageHeader';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import SubJobsTable from './SubJobsTable/SubJobsTable';
import StopSubJobDialog from './Dialogs/StopSubJobDialog';
import { useRequestJob } from './useRequestJob';

const JobPage = () => {
  const subJobsTableRef = useRef(null);
  const dispatch = useDispatch();
  const job = useStore(({ adcm }) => adcm.job.job);
  const jobDisplayName = job?.displayName ?? '';

  useRequestJob();

  useEffect(() => {
    if (jobDisplayName) {
      const jobBreadcrumbs = [{ href: '/jobs', label: 'Jobs' }, { label: jobDisplayName }];

      dispatch(setBreadcrumbs(jobBreadcrumbs));
    }
  }, [job?.id, jobDisplayName, dispatch]);

  return (
    <>
      <JobsPageHeader job={job} />
      <JobOverviewTable />
      <SubJobsTable ref={subJobsTableRef} />
      <StopSubJobDialog />
    </>
  );
};

export default JobPage;
