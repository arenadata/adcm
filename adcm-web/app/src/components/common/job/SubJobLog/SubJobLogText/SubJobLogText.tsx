import { useEffect, useRef, type RefObject } from 'react';
import CodeHighlighter from '@uikit/CodeHighlighter/CodeHighlighter';
import type { AdcmSubJobLogItemCustom, AdcmSubJobLogItemStd } from '@models/adcm';
import { useSubJobsLogsAutoScrollContext } from '@pages/JobsPage/SubJobPage/SubJobLogsAutoScroll/SubJobLogsAutoScroll.context';
import s from './SubJobLogText.module.scss';

interface SubJobLogTextProps {
  log: AdcmSubJobLogItemStd | AdcmSubJobLogItemCustom;
}

const SubJobLogText = ({ log }: SubJobLogTextProps) => {
  const content = log.content?.trim() || '';
  const language = log.format === 'json' ? 'json' : 'bash';
  const highlighterRef: RefObject<HTMLDivElement> = useRef(null);

  const autoScrollContextValue = useSubJobsLogsAutoScrollContext();

  useEffect(() => {
    autoScrollContextValue?.scrollToBottom();
  }, [log.content]);

  useEffect(() => {
    if (highlighterRef.current) {
      autoScrollContextValue?.setContainer(highlighterRef.current);
    }
  }, [highlighterRef.current]);

  return <CodeHighlighter contentRef={highlighterRef} className={s.subJobLogText} code={content} language={language} />;
};
export default SubJobLogText;
