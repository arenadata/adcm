import React from 'react';
import Statusable from '@uikit/Statusable/Statusable';
import { AdcmJob } from '@models/adcm';
import { jobStatusesMap } from '../JobPageTable/JobPageTable.constants';

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
