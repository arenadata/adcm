import type React from 'react';
import Statusable from '@uikit/Statusable/Statusable';
import type { AdcmSubJob } from '@models/adcm';
import { jobStatusesMap } from '../../JobPage/JobPage.constants';

interface SubJobNameProps {
  subJob: AdcmSubJob;
}

const SubJobName: React.FC<SubJobNameProps> = ({ subJob }) => (
  <Statusable status={jobStatusesMap[subJob.status]} size="large" iconPosition="left">
    {subJob.displayName}
  </Statusable>
);

export default SubJobName;
