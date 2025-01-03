import type React from 'react';
import { AdcmSubJobLogType, type AdcmSubJob, type AdcmSubJobLogItem } from '@models/adcm';
import SubJobLogCheck from './SubJobLogCheck/SubJobLogCheck';
import SubJobLogText from './SubJobLogText/SubJobLogText';

interface SubJobLogProps {
  subJob: AdcmSubJob;
  subJobLog: AdcmSubJobLogItem;
  isAutoScroll: boolean;
  setIsAutoScroll?: (isAutoScroll: boolean) => void;
}

const SubJobLog: React.FC<SubJobLogProps> = ({ subJob, subJobLog, isAutoScroll, setIsAutoScroll }) => {
  return renderLog({ subJob, subJobLog, isAutoScroll, setIsAutoScroll });
};
export default SubJobLog;

const renderLog = ({ subJob, subJobLog, isAutoScroll, setIsAutoScroll }: SubJobLogProps) => {
  if (subJobLog.type === AdcmSubJobLogType.Check) {
    return <SubJobLogCheck log={subJobLog} subJobStatus={subJob.status} />;
  }

  return <SubJobLogText isAutoScroll={isAutoScroll} setIsAutoScroll={setIsAutoScroll} log={subJobLog} />;
};
