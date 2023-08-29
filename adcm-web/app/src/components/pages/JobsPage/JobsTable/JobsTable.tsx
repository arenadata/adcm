import { Link, generatePath } from 'react-router-dom';
import { Table, TableRow, TableCell, IconButton } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { columns, linkByObjectTypeMap } from './JobsTable.constants';
import { setSortParams } from '@store/adcm/jobs/jobsTableSlice';
import { SortParams } from '@uikit/types/list.types';
import { openRestartDialog } from '@store/adcm/jobs/jobsActionsSlice';
import { AdcmJobStatus } from '@models/adcm';
import s from './JobsTable.module.scss';
import { dateToString } from '@utils/date/dateConvertUtils';
import { secondsToTime } from '@utils/time/timeConvertUtils';
import JobsStatusCell from '../../../common/Table/Cells/JobsStatusCell/JobsStatusCell';

const JobsTable = () => {
  const dispatch = useDispatch();
  const jobs = useStore((s) => s.adcm.jobs.jobs);
  const isLoading = useStore((s) => s.adcm.jobs.isLoading);
  const sortParams = useStore((s) => s.adcm.jobsTable.sortParams);

  const handleRestartClick = (id: number) => () => {
    dispatch(openRestartDialog(id));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  return (
    <Table isLoading={isLoading} columns={columns} sortParams={sortParams} onSorting={handleSorting}>
      {jobs.map((job) => {
        return (
          <TableRow key={job.id} className={s.jobRow}>
            <TableCell>{job.id}</TableCell>
            <JobsStatusCell status={job.status}>
              <Link to={generatePath('/jobs/:jobId', { jobId: job.id + '' })} className={s.jobRow__jobName}>
                {job.name}
              </Link>
            </JobsStatusCell>
            <TableCell>{job.status}</TableCell>
            <TableCell className={s.jobRow__jobObjects}>
              {job.objects?.map((object, i) => {
                return (
                  <span key={i}>
                    {i > 0 && ' / '}
                    <Link to={`/${linkByObjectTypeMap[object.type]}/${object.id}/`} key={object.id}>
                      {object.name}
                    </Link>
                  </span>
                );
              })}
            </TableCell>
            <TableCell>{secondsToTime(Math.round(+job.duration))}</TableCell>
            <TableCell>{dateToString(new Date(job.startTime))}</TableCell>
            <TableCell>{dateToString(new Date(job.endTime))}</TableCell>
            <TableCell hasIconOnly align="center">
              {job.status !== AdcmJobStatus.SUCCESS && (
                <IconButton icon="g1-return" size={32} title="Restart job" onClick={handleRestartClick(job.id)} />
              )}
              {job.status === AdcmJobStatus.SUCCESS && <IconButton icon="g1-stop" size={32} />}
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default JobsTable;
