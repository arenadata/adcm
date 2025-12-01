import type React from 'react';
import { AdcmSubJobLogType, type AdcmSubJob, type AdcmSubJobLogItem } from '@models/adcm';
import SubJobLogCheck from './SubJobLogCheck/SubJobLogCheck';
import SubJobLogText from './SubJobLogText/SubJobLogText';

interface SubJobLogProps {
  subJob: AdcmSubJob;
  subJobLog: AdcmSubJobLogItem;
}

const SubJobLog: React.FC<SubJobLogProps> = ({ subJob, subJobLog }) => {
  return renderLog({ subJob, subJobLog });
};
export default SubJobLog;

const renderLog = ({ subJob, subJobLog }: SubJobLogProps) => {
  if (subJobLog.type === AdcmSubJobLogType.Check) {
    return <SubJobLogCheck log={subJobLog} subJobStatus={subJob.status} />;
  }

  return <SubJobLogText log={subJobLog} />;
};
