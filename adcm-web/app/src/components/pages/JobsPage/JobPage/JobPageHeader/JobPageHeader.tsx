import React from 'react';
import s from './JobPageHeader.module.scss';
import EntityHeader from '@commonComponents/EntityHeader/EntityHeader';
import { useStore } from '@hooks';

const JobPageHeader: React.FC = () => {
  const task = useStore((s) => s.adcm.jobs.task);

  return <EntityHeader title={task.displayName} className={s.overviewHeader} />;
};

export default JobPageHeader;
