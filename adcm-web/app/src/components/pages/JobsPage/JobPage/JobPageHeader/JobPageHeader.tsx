import React from 'react';
import s from './JobPageHeader.module.scss';
import EntityHeader from '@commonComponents/EntityHeader/EntityHeader';
import { useStore } from '@hooks';
import JobPageHeaderName from './JobPageHeaderName';
import { orElseGet } from '@utils/checkUtils';

const JobPageHeader: React.FC = () => {
  const task = useStore((s) => s.adcm.jobs.task);

  return (
    <EntityHeader
      title={orElseGet(task, (task) => (
        <JobPageHeaderName job={task} />
      ))}
      className={s.overviewHeader}
    />
  );
};

export default JobPageHeader;
