import { Link, generatePath } from 'react-router-dom';
import { Table, TableRow, TableCell, IconButton, Button } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { columns } from './JobPageChildJobsTable.constants';
import { setSortParams } from '@store/adcm/jobs/jobsTableSlice';
import { SortParams } from '@uikit/types/list.types';
import { openStopDialog } from '@store/adcm/jobs/jobsActionsSlice';
import { AdcmJobStatus } from '@models/adcm';
import s from './JobPageChildJobsTable.module.scss';
import { getJobLog } from '@store/adcm/jobs/jobsSlice';
import DateTimeCell from '@commonComponents/Table/Cells/DateTimeCell';
import { secondsToDuration } from '@utils/date/timeConvertUtils';

const JobPageChildJobsTable = () => {
  const dispatch = useDispatch();
  const task = useStore((s) => s.adcm.jobs.task);
  const isLoading = useStore((s) => s.adcm.jobs.isLoading);

  const handleExpandClick = (id: number) => () => {
    dispatch(getJobLog(id));
  };

  const handleStopClick = (id: number) => () => {
    dispatch(openStopDialog(id));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  return (
    <Table variant="tertiary" isLoading={isLoading} columns={columns} onSorting={handleSorting}>
      {task.childJobs?.map((job) => {
        return (
          <TableRow key={job.id} className={s.jobRow}>
            <TableCell>
              <Link to={generatePath('/jobs/:jobId', { jobId: job.id + '' })} className={s.jobRow__jobName}>
                {job.displayName}
              </Link>
            </TableCell>
            <TableCell>{job.status}</TableCell>
            <TableCell>{secondsToDuration(job.duration)}</TableCell>
            <DateTimeCell value={job.startTime} />
            <DateTimeCell value={job.endTime} />
            <TableCell hasIconOnly align="center">
              {job.status === AdcmJobStatus.Success && (
                <IconButton icon="g1-stop" title="Stop the job" size={32} onClick={handleStopClick(job.id)} />
              )}
            </TableCell>
            <TableCell>
              <Button
                variant="secondary"
                iconLeft="dots"
                onClick={handleExpandClick(job.id)}
                disabled={false}
                placeholder="Expand"
              />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default JobPageChildJobsTable;
