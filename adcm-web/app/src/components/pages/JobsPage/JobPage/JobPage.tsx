import { useEffect, useRef } from 'react';
import { useDispatch, useStore } from '@hooks';
import ExpandableSwitch from '@uikit/Switch/ExpandableSwitch';
import JobOverviewTable from './JobOverviewTable/JobOverviewTable';
import JobsPageHeader from './JobPageHeader/JobPageHeader';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import SubJobsTable from './SubJobsTable/SubJobsTable';
import StopSubJobDialog from './Dialogs/StopSubJobDialog';
import { useRequestJob } from './useRequestJob';
import { useAutoScrollSubjobs } from './useAutoscrollSubjobs';
import s from './JobPage.module.scss';

const JobPage = () => {
  const subJobsTableRef = useRef(null);
  const dispatch = useDispatch();
  const job = useStore(({ adcm }) => adcm.job.job);
  const jobDisplayName = job?.displayName ?? '';

  useRequestJob();
  const { isAutoScroll, setIsAutoScroll } = useAutoScrollSubjobs(subJobsTableRef, job);

  useEffect(() => {
    if (jobDisplayName) {
      const jobBreadcrumbs = [{ href: '/jobs', label: 'Jobs' }, { label: jobDisplayName }];

      dispatch(setBreadcrumbs(jobBreadcrumbs));
    }
  }, [job?.id, jobDisplayName, dispatch]);

  const handleAutoScrollChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setIsAutoScroll(e.target.checked);
  };

  return (
    <>
      <JobsPageHeader job={job} />
      <JobOverviewTable />
      <SubJobsTable ref={subJobsTableRef} />
      <StopSubJobDialog />
      <div className={s.subJobsAutoScroll}>
        <ExpandableSwitch onChange={handleAutoScrollChange} label="Auto-open" isToggled={isAutoScroll} />
      </div>
    </>
  );
};

export default JobPage;
