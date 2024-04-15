import React from 'react';
import CodeHighlighterV2 from '@uikit/CodeHighlighterV2/CodeHighlighterV2';
import { AdcmJobLogItemCustom, AdcmJobLogItemStd } from '@models/adcm';
import s from './JobLogText.module.scss';

interface JobLogTextProps {
  log: AdcmJobLogItemStd | AdcmJobLogItemCustom;
}

const JobLogText: React.FC<JobLogTextProps> = ({ log }) => {
  const content = log.content?.trim() || '';
  const language = log.format === 'json' ? 'json' : 'bash';

  return <CodeHighlighterV2 className={s.jobLogText} code={content} lang={language} />;
};
export default JobLogText;
