import { Table, TableRow, TableCell } from '@uikit';
import { useStore } from '@hooks';
import DateTimeCell from '@commonComponents/Table/Cells/DateTimeCell';
import JobObjectsCell from '@commonComponents/Table/Cells/JobObjectsCell/JobObjectsCell';
import { JobActionIconButton } from '@commonComponents/job/JobActionIconButton/JobActionIconButton';
import { getJobTerminateActions } from '@commonComponents/job/jobTerminateActions';
import { secondsToDuration } from '@utils/date/timeConvertUtils';
import { orElseGet } from '@utils/checkUtils';
import type { SubJobTerminateMode } from '@store/adcm/jobs/subJobsActionsSlice';
import { columns } from './SubJobOverviewTable.constants';
import s from './SubJobOverviewTable.module.scss';

export interface SubJobOverviewTableProps {
  onAction: (mode: SubJobTerminateMode) => void;
}

const SubJobOverviewTable = ({ onAction }: SubJobOverviewTableProps) => {
  const subJob = useStore((s) => s.adcm.subJob.subJob);
  const isLoading = useStore((s) => s.adcm.subJob.isLoading);
  const { isSkipEnabled, isStopEnabled } = subJob
    ? getJobTerminateActions(subJob)
    : { isSkipEnabled: false, isStopEnabled: false };

  const handleSkipClick = () => onAction('skip');

  const handleStopClick = () => onAction('stop');

  return (
    <Table variant="quaternary" isLoading={isLoading} columns={columns}>
      {subJob && (
        <TableRow>
          <JobObjectsCell objects={subJob.parentTask?.objects} />
          <TableCell>{subJob.status}</TableCell>
          <TableCell>{orElseGet(subJob.duration ?? 0, secondsToDuration)}</TableCell>
          <DateTimeCell value={subJob.startTime ?? undefined} />
          <DateTimeCell value={subJob.endTime ?? undefined} />
          <TableCell hasIconOnly align="center">
            <div className={s.actions}>
              <JobActionIconButton
                icon="g1-graph-skip"
                label="Skip the subjob"
                disabled={!isSkipEnabled}
                onClick={handleSkipClick}
                data-test="subjob-page-skip"
              />
              <JobActionIconButton
                icon="g1-graph-stop"
                label="Stop the subjob"
                disabled={!isStopEnabled}
                onClick={handleStopClick}
                data-test="subjob-page-stop"
              />
            </div>
          </TableCell>
        </TableRow>
      )}
    </Table>
  );
};

export default SubJobOverviewTable;
