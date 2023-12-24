import React from 'react';
import CodeHighlighter from '@uikit/CodeHighlighter/CodeHighlighter';
import { AdcmJobLogItemCustom, AdcmJobLogItemStd } from '@models/adcm';

interface JobLogTextProps {
  log: AdcmJobLogItemStd | AdcmJobLogItemCustom;
}

const JobLogText: React.FC<JobLogTextProps> = ({ log }) => {
  const content = log.content?.trim() || '';
  const language = log.format === 'json' ? 'json' : 'accesslog';

  return <CodeHighlighter code={content} language={language} />;
};
export default JobLogText;
