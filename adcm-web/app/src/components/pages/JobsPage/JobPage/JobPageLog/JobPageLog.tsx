import React, { useState } from 'react';
import { useStore } from '@hooks';
import { Button, Tab, TabsBlock } from '@uikit';
import CodeHighlighter from '@uikit/CodeHighlighter/CodeHighlighter';
import { useRequestJobLogPage } from './useRequestJobLogPage';
import s from './JobPageLog.module.scss';
import { useLocation } from 'react-router-dom';
import { apiHost } from '@constants';

interface JobPageLogProps {
  id: number;
  isLinkEmpty?: boolean;
}

const getPathLogName = (pathname: string) => {
  const parts = pathname.split('/');
  const logNamePartPath = (parts[parts.length - 1] !== '' ? parts.at(-1) : parts.at(-2)) ?? '';
  return !isNaN(+logNamePartPath) ? 'stdout' : logNamePartPath;
};

const JobPageLog: React.FC<JobPageLogProps> = ({ id, isLinkEmpty = false }) => {
  useRequestJobLogPage(id);

  const childJob = useStore(({ adcm }) => adcm.jobs.task.childJobs.find((job) => job.id === id));
  const logs = childJob?.logs ?? [];

  const { pathname } = useLocation();
  const logNamePartPath = getPathLogName(pathname);

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
          Ansible [stdout]
        </Tab>
        <Tab to={isLinkEmpty ? '' : 'stderr'} onClick={getHandleTabClick('stderr')} isActive={logName === 'stderr'}>
          Ansible [stderr]
        </Tab>
      </TabsBlock>
      <CodeHighlighter code={log?.content.trim() || ''} language="javascript" className={s.codeHighlighter} />
      {log?.content && (
        <a href={downloadLink} download="download" target="_blank">
          <Button variant="secondary" className={s.jobLogDownloadButton} children="Download" />
        </a>
      )}
    </>
  );
};

export default JobPageLog;
