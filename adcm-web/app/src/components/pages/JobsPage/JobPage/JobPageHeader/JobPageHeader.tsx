import s from './JobPageHeader.module.scss';
import EntityHeader from '@commonComponents/EntityHeader/EntityHeader';
import JobPageHeaderName from './JobPageHeaderName';
import { orElseGet } from '@utils/checkUtils';
import type { AdcmJob, AdcmSubJob } from '@models/adcm';

export interface JobPageHeaderProps {
  job?: AdcmJob | AdcmSubJob;
}

const JobPageHeader = ({ job }: JobPageHeaderProps) => {
  return <EntityHeader title={orElseGet(job, (job) => <JobPageHeaderName job={job} />)} className={s.overviewHeader} />;
};

export default JobPageHeader;
