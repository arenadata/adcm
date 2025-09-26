import type React from 'react';
import { useCallback, useState } from 'react';
import { Button, ExpandableRowComponent, IconButton, Table, TableCell } from '@uikit';
import s from './ActionWizardOperation.module.scss';
import { columns } from './ActionWizardOperation.constants';
import { orElseGet } from '@utils/checkUtils';
import { openStopDialog } from '@store/adcm/jobs/subJobsActionsSlice';
import { useDispatch } from '@hooks';
import JobsStatusCell from '@commonComponents/Table/Cells/JobsStatusCell/JobsStatusCell';
import { secondsToDuration } from '@utils/date/timeConvertUtils';
import DateTimeCell from '@commonComponents/Table/Cells/DateTimeCell';
import { AdcmJobStatus } from '@models/adcm';
import type { AdcmJob, AdcmSubJob, AdcmSubJobLogItem } from '@models/adcm';
import { Link } from 'react-router-dom';
import ActionWizardOperationLog from '@uikit/ActionWizardSteps/ActionWizardOperation/ActionWizardOperationLog/ActionWizardOperationLog';

interface ActionWizardOperationProps {
  job: AdcmJob;
  subJobLog: AdcmSubJobLogItem[];
}

const ActionWizardOperation = ({ job, subJobLog }: ActionWizardOperationProps) => {
  const dispatch = useDispatch();
  const [expandableRows, setExpandableRows] = useState<Record<number, boolean>>({});

  const handleExpandClick = (id: number) => {
    setExpandableRows({
      ...expandableRows,
      [id]: expandableRows[id] === undefined ? true : !expandableRows[id],
    });
  };

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

  return (
    <Table variant="secondary" columns={columns}>
      {job?.childJobs?.map((subJob: AdcmSubJob) => (
        <ExpandableRowComponent
          key={subJob.id}
          colSpan={columns.length}
          isExpanded={expandableRows[subJob.id] || false}
          expandedContent={<ActionWizardOperationLog subJob={subJob} subJobLogs={subJobLog} />}
        >
          <JobsStatusCell status={subJob.status} className={s.subJobRow__subJobName}>
            <Link to={`/jobs/${job.id}/subjobs/${subJob.id}`} className="text-link">
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
          <TableCell hasIconOnly align="center">
            <Button variant="secondary" iconLeft="dots" onClick={() => handleExpandClick(subJob.id)} />
          </TableCell>
        </ExpandableRowComponent>
      ))}
    </Table>
  );
};

export default ActionWizardOperation;
