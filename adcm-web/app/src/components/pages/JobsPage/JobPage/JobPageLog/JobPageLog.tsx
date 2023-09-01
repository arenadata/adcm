import React from 'react';
import { useStore } from '@hooks';
import { Tab, TabsBlock } from '@uikit';
import CodeHighlighter from '@uikit/CodeHighlighter/CodeHighlighter';
import { useRequestJobLogPage } from './useRequestJobLogPage';
import s from './JobPageLog.module.scss';
import { useLocation } from 'react-router-dom';

interface JobPageLogProps {
  id?: number;
}

const JobPageLog: React.FC<JobPageLogProps> = ({ id }) => {
  useRequestJobLogPage(id);

  const logs = useStore(({ adcm }) => adcm.jobs.logs);
  const { pathname } = useLocation();

  const reportNameShift = pathname[pathname.length - 1] === '/' ? 1 : 0;
  const reportName = pathname.split('/').reverse()[reportNameShift];
  const log = logs.find((l) => l.type === reportName);

  return (
    <>
      <TabsBlock variant="secondary" className={s.jobLog}>
        <Tab to="stdout">Ansible [stdout]</Tab>
        <Tab to="stderr">Ansible [stderr]</Tab>
      </TabsBlock>
      <CodeHighlighter code={log?.content.trim() || ''} language="javascript" />
    </>
  );
};

export default JobPageLog;
