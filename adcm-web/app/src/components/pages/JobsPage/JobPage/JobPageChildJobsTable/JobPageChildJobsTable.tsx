import { Table, TableCell, IconButton, Button, ExpandableRowComponent } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { columns } from './JobPageChildJobsTable.constants';
import { setSortParams } from '@store/adcm/jobs/jobsTableSlice';
import { SortParams } from '@uikit/types/list.types';
import { openStopDialog } from '@store/adcm/jobs/jobsActionsSlice';
import { AdcmJobStatus } from '@models/adcm';
import s from './JobPageChildJobsTable.module.scss';
import DateTimeCell from '@commonComponents/Table/Cells/DateTimeCell';
import { secondsToDuration } from '@utils/date/timeConvertUtils';
import cn from 'classnames';
import JobPageLog from '../JobPageLog/JobPageLog';
import { useState } from 'react';
import JobsStatusCell from '@commonComponents/Table/Cells/JobsStatusCell/JobsStatusCell';

const JobPageChildJobsTable = () => {
  const dispatch = useDispatch();
  const task = useStore((s) => s.adcm.jobs.task);
  const isTaskLoading = useStore((s) => s.adcm.jobs.isTaskLoading);

  const [expandableRows, setExpandableRows] = useState<Record<number, boolean>>({});

  const handleExpandClick = (id: number) => () => {
    setExpandableRows({
      ...expandableRows,
      [id]: !expandableRows[id],
    });
  };

  const handleStopClick = (id: number) => () => {
    dispatch(openStopDialog(id));
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  return (
    <Table variant="tertiary" isLoading={isTaskLoading} columns={columns} onSorting={handleSorting}>
      {task.childJobs?.map((job) => {
        return (
          <ExpandableRowComponent
            key={job.id}
            colSpan={columns.length}
            isExpanded={expandableRows[job.id] ?? false}
            isInactive={!job.childJobs?.length}
            expandedContent={<JobPageLog id={job.id} isLinkEmpty={true} />}
            className={cn(s.rolesTable__roleRow, { [s.expandedRow]: expandableRows[job.id] })}
            expandedClassName={s.rolesTable__expandedRoleRow}
          >
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
                onClick={handleStopClick(job.id)}
                disabled={!job.isTerminatable || job.status !== AdcmJobStatus.Running}
              />
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
          </ExpandableRowComponent>
        );
      })}
    </Table>
  );
};

export default JobPageChildJobsTable;
