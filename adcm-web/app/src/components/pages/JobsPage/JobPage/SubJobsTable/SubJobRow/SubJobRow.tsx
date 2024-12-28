import type React from 'react';
import { Link } from 'react-router-dom';
import { AdcmJobStatus, type AdcmSubJob } from '@models/adcm';
import JobsStatusCell from '@commonComponents/Table/Cells/JobsStatusCell/JobsStatusCell';
import s from './SubJobRow.module.scss';
import { IconButton, TableRow, TableCell } from '@uikit';
import { secondsToDuration } from '@utils/date/timeConvertUtils';
import { orElseGet } from '@utils/checkUtils';
import DateTimeCell from '@commonComponents/Table/Cells/DateTimeCell';

interface SubJobRowProps {
  subJob: AdcmSubJob;
  handleStopClick: (event: React.MouseEvent<HTMLButtonElement>) => void;
}

const SubJobRow: React.FC<SubJobRowProps> = ({ subJob, handleStopClick }) => {
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
        <IconButton
          icon="g1-skip"
          title="Skip the subjob"
          size={32}
          onClick={handleStopClick}
          disabled={!subJob.isTerminatable || subJob.status !== AdcmJobStatus.Running}
          data-subjobid={subJob.id}
        />
      </TableCell>
    </TableRow>
  );
};

export default SubJobRow;
