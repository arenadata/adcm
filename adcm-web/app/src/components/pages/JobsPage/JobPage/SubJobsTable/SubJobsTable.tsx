import React, { useCallback, forwardRef } from 'react';
import { Table } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { columns } from './SubJobsTable.constants';
import { setSortParams } from '@store/adcm/jobs/jobsTableSlice';
import type { SortParams } from '@uikit/types/list.types';
import { openStopDialog } from '@store/adcm/jobs/subJobsActionsSlice';
import { orElseGet } from '@utils/checkUtils';
import SubJobRow from './SubJobRow/SubJobRow';
import s from './SubJobsTable.module.scss';

const SubJobsTable = forwardRef<HTMLTableElement>((_, ref) => {
  const dispatch = useDispatch();

  const job = useStore((s) => s.adcm.job.job);
  const isLoading = useStore((s) => s.adcm.job.isLoading);

  const handleStopClick = useCallback(
    ({ currentTarget }: React.MouseEvent<HTMLButtonElement>) => {
      // eslint want that jobId (in camelCase), but JSX demands set data attributes in lowercase
      // eslint-disable-next-line spellcheck/spell-checker
      const subJobId = orElseGet(currentTarget.dataset.subjobid, Number, null);
      if (subJobId) {
        dispatch(openStopDialog(subJobId));
      }
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
      {job?.childJobs?.map((subJob) => <SubJobRow key={subJob.id} subJob={subJob} handleStopClick={handleStopClick} />)}
    </Table>
  );
});

export default SubJobsTable;
