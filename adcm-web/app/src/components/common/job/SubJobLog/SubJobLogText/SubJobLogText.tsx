import type { AdcmSubJobLogItemCustom, AdcmSubJobLogItemStd } from '@models/adcm';
import { useSubJobsLogsAutoScrollContext } from '@pages/JobsPage/SubJobPage/SubJobLogsAutoScroll/SubJobLogsAutoScroll.context';
import s from './SubJobLogText.module.scss';
import MonacoCodeViewer from '@uikit/MonacoCodeEditor/MonacoCodeViewer/MonacoCodeViewer.tsx';

interface SubJobLogTextProps {
  log: AdcmSubJobLogItemStd | AdcmSubJobLogItemCustom;
}

const SubJobLogText = ({ log }: SubJobLogTextProps) => {
  const content = log.content?.trim() || '';
  const language = log.format === 'json' ? 'json' : 'bash';
  const autoScrollContext = useSubJobsLogsAutoScrollContext();

  return (
    <MonacoCodeViewer
      className={s.subJobLogText}
      code={content}
      language={language}
      scrollToEnd={autoScrollContext?.isAutoScroll}
    />
  );
};

export default SubJobLogText;
