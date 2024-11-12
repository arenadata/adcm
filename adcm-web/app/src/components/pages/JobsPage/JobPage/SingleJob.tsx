import React from 'react';
import s from '@pages/JobsPage/JobPage/JobPageChildJobsTable/JobPageChildJobsTable.module.scss';
import ExpandableSwitch from '@uikit/Switch/ExpandableSwitch';
import JobPageLog from '@pages/JobsPage/JobPage/JobPageLog/JobPageLog';
import { useJobLogAutoScroll } from '@pages/JobsPage/JobPage/useJobLogAutoScroll';
import type { AdcmTask } from '@models/adcm';

interface SingleJobProps {
  task: AdcmTask;
}

const SingleJob = ({ task }: SingleJobProps) => {
  const { isUserScrollRef, isAutoScrollState, setIsAutoScroll, toggleIsAutoScroll } = useJobLogAutoScroll(task);

  return (
    <div>
      <JobPageLog
        isUserScrollRef={isUserScrollRef}
        isAutoScroll={isAutoScrollState}
        setIsAutoScroll={setIsAutoScroll}
        id={task.childJobs[0].id}
      />
      <div className={s.jobsPageAutoScroll}>
        <ExpandableSwitch onChange={toggleIsAutoScroll} label="Auto-open" isToggled={isAutoScrollState} />
      </div>
    </div>
  );
};

export default SingleJob;
