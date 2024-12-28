import { useEffect } from 'react';
import { useStore, useDispatch } from '@hooks';
import ExpandableSwitch from '@uikit/Switch/ExpandableSwitch';
import JobPageHeader from '../JobPage/JobPageHeader/JobPageHeader';
import StopSubJobDialog from '../JobPage/Dialogs/StopSubJobDialog';
import SubJobOverviewTable from './SubJobOverviewTable/SubJobOverviewTable';
import SubJobLogs from './SubJobLogs/SubJobLogs';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import { openStopDialog } from '@store/adcm/jobs/subJobsActionsSlice';
import { useRequestSubJob } from './useRequestSubJob';
import { useAutoScrollLog } from './useAutoScrollLog';
import s from './SubJobPage.module.scss';

const SubJobPage = () => {
  const dispatch = useDispatch();
  useRequestSubJob();

  const subJob = useStore(({ adcm }) => adcm.subJob.subJob);

  const { isAutoScroll, setIsAutoScroll } = useAutoScrollLog(subJob);

  useEffect(() => {
    if (subJob) {
      const jobBreadcrumbs = [
        { href: '/jobs', label: 'Jobs' },
        { label: subJob.parentTask.displayName, href: `/jobs/${subJob.parentTask.id}` },
        { label: subJob.displayName },
      ];

      dispatch(setBreadcrumbs(jobBreadcrumbs));
    }
  }, [subJob, subJob?.displayName, subJob?.parentTask.id, subJob?.parentTask.displayName, dispatch]);

  const handleStop = () => {
    if (subJob) {
      dispatch(openStopDialog(subJob.id));
    }
  };

  const handleAutoScrollChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setIsAutoScroll(e.target.checked);
  };

  return (
    <>
      <JobPageHeader job={subJob} />
      <div className={s.subJobInfo}>
        <SubJobOverviewTable onStop={handleStop} />
        <div className={s.logsWrapper}>
          <SubJobLogs isAutoScroll={isAutoScroll} setIsAutoScroll={setIsAutoScroll} />
        </div>
      </div>
      <StopSubJobDialog />
      <div className={s.subJobLogAutoScroll}>
        <ExpandableSwitch onChange={handleAutoScrollChange} label="Auto-open" isToggled={isAutoScroll} />
      </div>
    </>
  );
};

export default SubJobPage;
