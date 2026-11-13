import { useEffect, useMemo, useRef, useState } from 'react';
import { useDispatch, useStore } from '@hooks';
import JobOverviewTable from './JobOverviewTable/JobOverviewTable';
import JobsPageHeader from './JobPageHeader/JobPageHeader';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import SubJobsTable from './SubJobsTable/SubJobsTable';
import StopSubJobDialog from './Dialogs/StopSubJobDialog';
import StopJobGroupDialog from '@commonComponents/job/StopJobGroupDialog/StopJobGroupDialog';
import { useRequestJob } from './useRequestJob';
import JobViewToggle, { type JobViewMode } from '@commonComponents/JobViewToggle/JobViewToggle';
import JobExecutionGraphPanel from './JobExecutionGraphPanel/JobExecutionGraphPanel';
import { NotificationBlock } from '@uikit';
import { shouldShowCeleryWorkersNote } from '@commonComponents/JobExecutionGraph';
import s from './JobPage.module.scss';

const JobPage = () => {
  const subJobsTableRef = useRef(null);
  const dispatch = useDispatch();
  const job = useStore(({ adcm }) => adcm.job.job);
  const executionPlan = useStore(({ adcm }) => adcm.job.executionPlan);
  const [viewMode, setViewMode] = useState<JobViewMode>('table');
  const jobDisplayName = job?.displayName ?? '';
  const showCeleryWorkersNote = useMemo(() => shouldShowCeleryWorkersNote(executionPlan), [executionPlan]);

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
      <div className={s.viewToggle}>
        <JobViewToggle viewMode={viewMode} onChange={setViewMode} />
      </div>
      {viewMode === 'graph' && showCeleryWorkersNote && (
        <NotificationBlock className={s.graphNote}>
          In Celery Worker mode, tasks can be executed in parallel
        </NotificationBlock>
      )}
      {viewMode === 'table' ? <SubJobsTable ref={subJobsTableRef} /> : <JobExecutionGraphPanel />}
      <StopSubJobDialog />
      {job && <StopJobGroupDialog jobId={job.id} />}
    </>
  );
};

export default JobPage;
