import { Table, TableRow, TableCell, IconButton } from '@uikit';
import { useStore } from '@hooks';
import DateTimeCell from '@commonComponents/Table/Cells/DateTimeCell';
import { secondsToDuration } from '@utils/date/timeConvertUtils';
import { orElseGet } from '@utils/checkUtils';
import { columns, jobStatusesMap } from './SubJobOverviewTable.constants';
import { AdcmJobStatus } from '@models/adcm';

export interface SubJobOverviewTableProps {
  onStop: () => void;
}

const SubJobOverviewTable = ({ onStop }: SubJobOverviewTableProps) => {
  const subJob = useStore((s) => s.adcm.subJob.subJob);
  const isLoading = useStore((s) => s.adcm.subJob.isLoading);

  return (
    <Table variant="quaternary" isLoading={isLoading} columns={columns}>
      {subJob && (
        <TableRow>
          <TableCell>{jobStatusesMap[subJob.status]}</TableCell>
          <TableCell>{orElseGet(subJob.duration ?? 0, secondsToDuration)}</TableCell>
          <DateTimeCell value={subJob.startTime ?? undefined} />
          <DateTimeCell value={subJob.endTime ?? undefined} />
          <TableCell hasIconOnly align="center">
            <IconButton
              icon="g1-skip"
              title="Skip the subjob"
              size={32}
              onClick={onStop}
              disabled={!subJob.isTerminatable || subJob.status !== AdcmJobStatus.Running}
            />
          </TableCell>
        </TableRow>
      )}
    </Table>
  );
};

export default SubJobOverviewTable;
