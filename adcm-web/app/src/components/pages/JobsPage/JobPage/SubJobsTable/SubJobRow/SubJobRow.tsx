import type React from 'react';
import { Link } from 'react-router-dom';
import type { AdcmSubJob } from '@models/adcm';
import JobsStatusCell from '@commonComponents/Table/Cells/JobsStatusCell/JobsStatusCell';
import { JobActionIconButton } from '@commonComponents/job/JobActionIconButton/JobActionIconButton';
import { getJobTerminateActions } from '@commonComponents/job/jobTerminateActions';
import s from './SubJobRow.module.scss';
import { TableRow, TableCell } from '@uikit';
import { secondsToDuration } from '@utils/date/timeConvertUtils';
import { orElseGet } from '@utils/checkUtils';
import DateTimeCell from '@commonComponents/Table/Cells/DateTimeCell';
import type { SubJobTerminateMode } from '@store/adcm/jobs/subJobsActionsSlice';

interface SubJobRowProps {
  subJob: AdcmSubJob;
  onAction: (subJob: AdcmSubJob, mode: SubJobTerminateMode) => void;
}

const SubJobRow: React.FC<SubJobRowProps> = ({ subJob, onAction }) => {
  const { isSkipEnabled, isStopEnabled } = getJobTerminateActions(subJob);

  const handleSkipClick = () => {
    onAction(subJob, 'skip');
  };

  const handleStopClick = () => {
    onAction(subJob, 'stop');
  };

  return (
    <TableRow>
      <JobsStatusCell status={subJob.status} className={s.subJobRow__subJobName}>
        <Link to={`subjobs/${subJob.id}`} className="text-link">
          {orElseGet(subJob.displayName || null)}
        </Link>
      </JobsStatusCell>
      <TableCell>{subJob.status}</TableCell>
      <TableCell>{orElseGet(subJob.duration ?? 0, secondsToDuration)}</TableCell>
      <DateTimeCell value={subJob.startTime ?? undefined} />
      <DateTimeCell value={subJob.endTime ?? undefined} />
      <TableCell hasIconOnly align="center">
        <div className={s.subJobRow__actions}>
          <JobActionIconButton
            icon="g1-graph-skip"
            label="Skip the subjob"
            disabled={!isSkipEnabled}
            onClick={handleSkipClick}
            data-test="subjob-skip"
          />
          <JobActionIconButton
            icon="g1-graph-stop"
            label="Terminate the subjob"
            disabled={!isStopEnabled}
            onClick={handleStopClick}
            data-test="subjob-stop"
          />
        </div>
      </TableCell>
    </TableRow>
  );
};

export default SubJobRow;
