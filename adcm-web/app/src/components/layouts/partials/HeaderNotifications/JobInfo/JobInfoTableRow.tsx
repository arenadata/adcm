import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import s from './JobInfo.module.scss';
import JobsStatusIcon from '@commonComponents/JobsStatusIcon/JobsStatusIcon';
import { ConditionalWrapper, IconButton, Tooltip, FlexGroup } from '@uikit';
import type { AdcmJob } from '@models/adcm';
import { Link } from 'react-router-dom';
import { orElseGet } from '@utils/checkUtils';
import cn from 'classnames';

const symbolsNumberToShowTooltip = 16;

interface JobInfoTableRowProps {
  job: AdcmJob;
  areAllExpanded: boolean;
}

const JobInfoTableRow: React.FC<JobInfoTableRowProps> = ({ job, areAllExpanded }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleExpandClick = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, [setIsExpanded]);

  useEffect(() => {
    setIsExpanded(areAllExpanded);
  }, [areAllExpanded, setIsExpanded]);

  const jobName = orElseGet(job.displayName || null);

  return (
    <tr>
      <td className={s.job__id}>{job.id}</td>
      <td className={s.job__link}>
        <FlexGroup gap="8px">
          <JobsStatusIcon
            //
            dataTest={`job_status_${job.status}`}
            size={14}
            status={job.status}
            className={s.job__icon}
          />
          <ConditionalWrapper
            Component={Tooltip}
            isWrap={jobName.length > symbolsNumberToShowTooltip}
            label={jobName}
            placement="bottom-start"
          >
            <Link className="text-link" to={`/jobs/${job.id}`}>
              {jobName}
            </Link>
          </ConditionalWrapper>
        </FlexGroup>

        {isExpanded && (
          <div className={s.job__objectName}>
            {job.objects.map(({ id, name }) => (
              <span key={`${name}_${id}`}>{name}</span>
            ))}
          </div>
        )}
      </td>
      <td className={s.job__expandButton}>
        <IconButton
          icon="chevron"
          size="small"
          onClick={handleExpandClick}
          className={cn(s.button, {
            [s.button_isExpanded]: isExpanded,
          })}
        />
      </td>
    </tr>
  );
};

export default JobInfoTableRow;
