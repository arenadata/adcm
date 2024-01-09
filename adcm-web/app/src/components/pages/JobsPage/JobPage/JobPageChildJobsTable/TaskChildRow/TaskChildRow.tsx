import React from 'react';
import { AdcmJob, AdcmJobStatus } from '@models/adcm';
import JobsStatusCell from '@commonComponents/Table/Cells/JobsStatusCell/JobsStatusCell';
import s from '@pages/JobsPage/JobPage/JobPageChildJobsTable/JobPageChildJobsTable.module.scss';
import { Button, IconButton, TableCell } from '@uikit';
import { secondsToDuration } from '@utils/date/timeConvertUtils';
import DateTimeCell from '@commonComponents/Table/Cells/DateTimeCell';

interface TaskChildRowProps {
  job: AdcmJob;
  handleExpandClick: (event: React.MouseEvent<HTMLButtonElement>) => void;
  handleStopClick: (event: React.MouseEvent<HTMLButtonElement>) => void;
}

const TaskChildRow: React.FC<TaskChildRowProps> = ({ job, handleExpandClick, handleStopClick }) => {
  return (
    <>
      <JobsStatusCell status={job.status} className={s.jobRow__jobName}>
        {job.displayName}
      </JobsStatusCell>
      <TableCell>{job.status}</TableCell>
      <TableCell>{secondsToDuration(job.duration)}</TableCell>
      <DateTimeCell value={job.startTime} />
      <DateTimeCell value={job.endTime} />
      <TableCell hasIconOnly align="center">
        <IconButton
          icon="g1-skip"
          title="Stop the job"
          size={32}
          onClick={handleStopClick}
          disabled={!job.isTerminatable || job.status !== AdcmJobStatus.Running}
          data-jobid={job.id}
        />
      </TableCell>
      <TableCell>
        <Button
          variant="secondary"
          iconLeft="dots"
          data-jobid={job.id}
          onClick={handleExpandClick}
          placeholder="Expand"
        />
      </TableCell>
    </>
  );
};

export default TaskChildRow;
