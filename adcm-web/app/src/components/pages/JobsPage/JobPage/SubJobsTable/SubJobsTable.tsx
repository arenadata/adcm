import { useCallback, forwardRef } from 'react';
import { Table } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { columns } from './SubJobsTable.constants';
import { setSortParams } from '@store/adcm/jobs/jobsTableSlice';
import type { SortParams } from '@uikit/types/list.types';
import { openStopDialog, type SubJobTerminateMode } from '@store/adcm/jobs/subJobsActionsSlice';
import type { AdcmSubJob } from '@models/adcm';
import SubJobRow from './SubJobRow/SubJobRow';
import s from './SubJobsTable.module.scss';

const SubJobsTable = forwardRef<HTMLTableElement>((_, ref) => {
  const dispatch = useDispatch();

  const job = useStore((s) => s.adcm.job.job);
  const isLoading = useStore((s) => s.adcm.job.isLoading);

  const handleAction = useCallback(
    (subJob: AdcmSubJob, mode: SubJobTerminateMode) => {
      dispatch(openStopDialog({ id: subJob.id, mode, displayName: subJob.displayName }));
    },
    [dispatch],
  );

  const handleSorting = useCallback(
    (sortParams: SortParams) => {
      dispatch(setSortParams(sortParams));
    },
    [dispatch],
  );

  return (
    <Table
      ref={ref}
      variant="secondary"
      isLoading={isLoading}
      columns={columns}
      className={s.subJobsTable}
      onSorting={handleSorting}
    >
      {job?.childJobs?.map((subJob) => (
        <SubJobRow key={subJob.id} subJob={subJob} onAction={handleAction} />
      ))}
    </Table>
  );
});

export default SubJobsTable;
