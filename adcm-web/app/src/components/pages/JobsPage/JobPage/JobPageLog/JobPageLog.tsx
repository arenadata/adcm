import React, { useState } from 'react';
import { useStore } from '@hooks';
import { Button, Tab, TabsBlock } from '@uikit';
import CodeHighlighter from '@uikit/CodeHighlighter/CodeHighlighter';
import { useRequestJobLogPage } from './useRequestJobLogPage';
import s from './JobPageLog.module.scss';
import { Link, useLocation } from 'react-router-dom';
import { apiHost } from '@constants';

interface JobPageLogProps {
  id: number;
  isLinkEmpty?: boolean;
}

const getPathLogName = (pathname: string) => {
  const parts = pathname.split('/');
  const logNamePartPath = (parts[parts.length - 1] !== '' ? parts.at(-1) : parts.at(-2)) ?? '';
  return !isNaN(+logNamePartPath) ? 'stdout' : '';
};

const JobPageLog: React.FC<JobPageLogProps> = ({ id, isLinkEmpty = false }) => {
  useRequestJobLogPage(id);

  const childJob = useStore(({ adcm }) => adcm.jobs.task.childJobs.find((job) => job.id === id));
  const logs = childJob?.logs ?? [];

  const { pathname } = useLocation();
  const logNamePartPath = getPathLogName(pathname);

  const [logNameClick, setLogNameClick] = useState<string>('stdout');
  const handleTabClick = (log: string) => () => {
    setLogNameClick(log);
  };

  const logName = isLinkEmpty ? logNameClick : logNamePartPath;
  const log = logs.find((log) => log.type === logName);

  const downloadLink = `${apiHost}/api/v2/jobs/${childJob?.id}/logs/${log?.type === 'stdout' ? 1 : 2}/download/`;

  return (
    <>
      <TabsBlock variant="secondary" className={s.jobLog}>
        <Tab to={isLinkEmpty ? '' : 'stdout'} onClick={handleTabClick('stdout')} isActive={logName === 'stdout'}>
          Ansible [stdout]
        </Tab>
        <Tab to={isLinkEmpty ? '' : 'stderr'} onClick={handleTabClick('stderr')} isActive={logName === 'stderr'}>
          Ansible [stderr]
        </Tab>
      </TabsBlock>
      <CodeHighlighter code={log?.content.trim() || ''} language="javascript" className={s.codeHighlighter} />
      <Link to={downloadLink} download="download" target="_blank">
        <Button variant="secondary" className={s.jobLogDownloadButton} children="Download" />
      </Link>
    </>
  );
};

export default JobPageLog;
