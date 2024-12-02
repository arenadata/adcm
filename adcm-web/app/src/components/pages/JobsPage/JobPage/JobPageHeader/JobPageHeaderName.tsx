import React from 'react';
import Statusable from '@uikit/Statusable/Statusable';
import type { AdcmJob } from '@models/adcm';
import { jobStatusesMap } from '../JobPage.constants';

interface JobPageHeaderNameProps {
  job: AdcmJob;
}

const JobPageHeaderName: React.FC<JobPageHeaderNameProps> = ({ job }) => {
  return (
    <Statusable status={jobStatusesMap[job.status]} size="large" iconPosition="left">
      {job.displayName}
    </Statusable>
  );
};

export default JobPageHeaderName;
