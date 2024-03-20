import React, { useCallback } from 'react';
import { Table, ExpandableRowComponent } from '@uikit';
import { useDispatch, useExpandableTable, useStore } from '@hooks';
import { columns } from './JobPageChildJobsTable.constants';
import { setSortParams } from '@store/adcm/jobs/jobsTableSlice';
import { SortParams } from '@uikit/types/list.types';
import { openStopDialog } from '@store/adcm/jobs/jobsActionsSlice';
import { AdcmJob } from '@models/adcm';
import JobPageLog from '../JobPageLog/JobPageLog';
import { orElseGet } from '@utils/checkUtils';
import TaskChildRow from './TaskChildRow/TaskChildRow';

const callForJob = (el: HTMLElement, callback: (jobId: number) => void) => {
  // eslint want that jobId (in camelCase), but JSX demands set data attributes in lowercase
  // eslint-disable-next-line spellcheck/spell-checker
  const jobId = orElseGet(el.dataset.jobid, Number, null);
  if (jobId) {
    callback(jobId);
  }
};

const JobPageChildJobsTable = () => {
  const dispatch = useDispatch();
  const task = useStore((s) => s.adcm.jobs.task);
  const isTaskLoading = useStore((s) => s.adcm.jobs.isTaskLoading);

  const { expandableRows, toggleRow } = useExpandableTable<AdcmJob['id']>();

  const handleExpandClick = useCallback(
    ({ currentTarget }: React.MouseEvent<HTMLButtonElement>) => {
      callForJob(currentTarget, (jobId) => {
        toggleRow(jobId);
      });
    },
    [toggleRow],
  );

  const handleStopClick = useCallback(
    ({ currentTarget }: React.MouseEvent<HTMLButtonElement>) => {
      callForJob(currentTarget, (jobId) => {
        dispatch(openStopDialog(jobId));
      });
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
    <Table variant="tertiary" isLoading={isTaskLoading} columns={columns} onSorting={handleSorting}>
      {task.childJobs?.map((job) => {
        return (
          <ExpandableRowComponent
            key={job.id}
            colSpan={columns.length}
            isExpanded={expandableRows.has(job.id)}
            expandedContent={<JobPageLog id={job.id} />}
          >
            <TaskChildRow job={job} handleExpandClick={handleExpandClick} handleStopClick={handleStopClick} />
          </ExpandableRowComponent>
        );
      })}
    </Table>
  );
};

export default JobPageChildJobsTable;
