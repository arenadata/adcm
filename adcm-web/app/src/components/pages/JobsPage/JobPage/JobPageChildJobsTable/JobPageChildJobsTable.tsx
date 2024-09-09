import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Table, ExpandableRowComponent } from '@uikit';
import { useDispatch, useExpandableTable, useStore } from '@hooks';
import { columns } from './JobPageChildJobsTable.constants';
import { setSortParams } from '@store/adcm/jobs/jobsTableSlice';
import { SortParams } from '@uikit/types/list.types';
import { openStopDialog } from '@store/adcm/jobs/jobsActionsSlice';
import type { AdcmJob } from '@models/adcm';
import { AdcmJobStatus } from '@models/adcm';
import JobPageLog from '../JobPageLog/JobPageLog';
import { orElseGet } from '@utils/checkUtils';
import TaskChildRow from './TaskChildRow/TaskChildRow';
import ExpandableSwitch from '@uikit/Switch/ExpandableSwitch';
import s from './JobPageChildJobsTable.module.scss';
import { useParams } from 'react-router-dom';

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
  const [lastViewedJobId, setLastViewedJobId] = useState<number | null>(null);
  const { expandableRows, toggleRow, changeExpandedRowsState, setExpandableRows } = useExpandableTable<AdcmJob['id']>();

  const isUserScrollRef = useRef(false);
  const isAutoScrollRef = useRef(true);
  const [isAutoScrollState, setIsAutoScrollState] = useState(true);
  const isTaskWasStartedRef = useRef(false);
  const props = useParams();
  const { withAutoStop } = props;

  const setIsAutoScroll = (state: boolean) => {
    if (!withAutoStop) return;
    setIsAutoScrollState(state);
    isAutoScrollRef.current = state;
  };

  const toggleIsAutoScroll = () => {
    isAutoScrollRef.current = !isAutoScrollRef.current;
    setIsAutoScrollState((prev) => !prev);

    if (!isAutoScrollRef.current || !lastViewedJobId) return;
    setExpandableRows(new Set([lastViewedJobId]));
  };

  const updateRowsState = () => {
    if (!task.childJobs || !isAutoScrollRef.current || !isTaskWasStartedRef.current) return;

    if (lastViewedJobId === null) {
      const firstJobId = task.childJobs[0].id;
      setLastViewedJobId(firstJobId);
      changeExpandedRowsState([{ key: firstJobId, isExpand: true }]);
      return;
    }

    const lastViewedJob = task.childJobs.find((job) => job.id === lastViewedJobId);

    if (
      !lastViewedJob ||
      lastViewedJob.status === AdcmJobStatus.Running ||
      lastViewedJob.status === AdcmJobStatus.Created
    ) {
      return;
    }

    let nextJob =
      task.childJobs.findLast((child) => child.status === AdcmJobStatus.Running) ||
      task.childJobs.find((child) => child.status === AdcmJobStatus.Created);

    if (!nextJob) {
      const lastJobIndex = task.childJobs.indexOf(lastViewedJob);

      if (lastJobIndex === -1 || !task.childJobs[lastJobIndex + 1]) return;

      nextJob = task.childJobs[lastJobIndex + 1];
    }

    setLastViewedJobId(nextJob.id);
    setExpandableRows(new Set([nextJob.id]));
  };

  useEffect(() => {
    const onUserScrollHandler = () => {
      if (isUserScrollRef.current) {
        setIsAutoScroll(false);
      }
    };

    const onEndHandler = () => {
      isUserScrollRef.current = true;
    };

    if (task.status === AdcmJobStatus.Running && isAutoScrollState) {
      window.addEventListener('scroll', onUserScrollHandler);
      window.addEventListener('scrollend', onEndHandler);
    }

    return () => {
      window.removeEventListener('scroll', onUserScrollHandler);
      window.removeEventListener('scrollend', onEndHandler);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [task.status, isAutoScrollRef, isAutoScrollState]);

  useEffect(() => {
    if (task.status === AdcmJobStatus.Running && lastViewedJobId === null && !isTaskWasStartedRef.current) {
      isTaskWasStartedRef.current = true;
    }

    if (task.status === AdcmJobStatus.Failed) {
      const lastFailedJob = task.childJobs.findLast((child) => child.status === AdcmJobStatus.Failed);
      if (!lastFailedJob) return;
      setExpandableRows(new Set([lastFailedJob.id]));
      return;
    }

    updateRowsState();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [task, lastViewedJobId, isAutoScrollState]);

  const handleExpandClick = useCallback(
    ({ currentTarget }: React.MouseEvent<HTMLButtonElement>) => {
      callForJob(currentTarget, (jobId) => {
        toggleRow(jobId);
        setIsAutoScroll(false);
      });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [task, toggleRow],
  );

  const handleStopClick = useCallback(
    ({ currentTarget }: React.MouseEvent<HTMLButtonElement>) => {
      callForJob(currentTarget, (jobId) => {
        setIsAutoScroll(false);
        dispatch(openStopDialog(jobId));
      });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [dispatch],
  );

  const handleSorting = useCallback(
    (sortParams: SortParams) => {
      dispatch(setSortParams(sortParams));
    },
    [dispatch],
  );

  return (
    <>
      <Table variant="tertiary" isLoading={isTaskLoading} columns={columns} onSorting={handleSorting}>
        {task.childJobs?.map((job) => {
          return (
            <ExpandableRowComponent
              key={job.id}
              colSpan={columns.length}
              isExpanded={expandableRows.has(job.id)}
              expandedContent={
                <JobPageLog
                  isUserScrollRef={isUserScrollRef}
                  isAutoScroll={isAutoScrollState}
                  setIsAutoScroll={setIsAutoScroll}
                  id={job.id}
                />
              }
            >
              <TaskChildRow job={job} handleExpandClick={handleExpandClick} handleStopClick={handleStopClick} />
            </ExpandableRowComponent>
          );
        })}
      </Table>
      <div className={s.jobsPageAutoScroll}>
        <ExpandableSwitch onChange={toggleIsAutoScroll} label="Auto-open" isToggled={isAutoScrollState} />
      </div>
    </>
  );
};

export default JobPageChildJobsTable;
