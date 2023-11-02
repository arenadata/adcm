import React, { useState } from 'react';
import { useStore } from '@hooks';
import { Button, Tab, TabsBlock } from '@uikit';
import CodeHighlighter from '@uikit/CodeHighlighter/CodeHighlighter';
import { useRequestJobLogPage } from './useRequestJobLogPage';
import s from './JobPageLog.module.scss';
import { useParams } from 'react-router-dom';
import { apiHost } from '@constants';
import JobLogCheck from '@commonComponents/job/JobLog/JobLogCheck/JobLogCheck';
import { AdcmJobLogItemCheck, AdcmJobLogItemStd } from '@models/adcm';
import { getStatusLabel } from '@utils/humanizationUtils';

interface JobPageLogProps {
  id: number;
  isLinkEmpty?: boolean;
}

const JobPageLog: React.FC<JobPageLogProps> = ({ id, isLinkEmpty = false }) => {
  useRequestJobLogPage(id);

  const childJob = useStore(({ adcm }) => adcm.jobs.task.childJobs.find((job) => job.id === id));
  const logs = useStore(({ adcm }) => adcm.jobs.jobLogs[id]) ?? [];

  const params = useParams();
  const logNamePartPath = params['*'] || 'stdout';

  const [logNameClick, setLogNameClick] = useState<string>('stdout');
  const getHandleTabClick = (log: string) => () => {
    setLogNameClick(log);
  };

  const logName = isLinkEmpty ? logNameClick : logNamePartPath;
  const log = logs.find((log) => log.type === logName);

  const downloadLink = `${apiHost}/api/v2/jobs/${childJob?.id}/logs/${log?.id}/download/`;

  return (
    <>
      <TabsBlock variant="secondary" className={s.jobLog}>
        <Tab to={isLinkEmpty ? '' : 'stdout'} onClick={getHandleTabClick('stdout')} isActive={logName === 'stdout'}>
          {getStatusLabel(logs[0]?.name ?? '')} [stdout]
        </Tab>
        <Tab to={isLinkEmpty ? '' : 'stderr'} onClick={getHandleTabClick('stderr')} isActive={logName === 'stderr'}>
          {getStatusLabel(logs[1]?.name ?? '')} [stderr]
        </Tab>
        {logs[2] && (
          <Tab to={isLinkEmpty ? '' : 'check'} onClick={getHandleTabClick('check')} isActive={logName === 'check'}>
            {getStatusLabel(logs[2]?.name ?? '')} [check]
          </Tab>
        )}
      </TabsBlock>
      {logName === 'check' && !!log && <JobLogCheck log={log as AdcmJobLogItemCheck} />}
      {logName !== 'check' && (
        <CodeHighlighter
          code={(log as AdcmJobLogItemStd)?.content.trim() || ''}
          language="accesslog"
          className={s.codeHighlighter}
        />
      )}
      {log?.content && (
        <a href={downloadLink} download="download" target="_blank">
          <Button variant="secondary" className={s.jobLogDownloadButton} children="Download" />
        </a>
      )}
    </>
  );
};

export default JobPageLog;
