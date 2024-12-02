import { Table, TableRow, TableCell } from '@uikit';
import { useStore } from '@hooks';
import { columns } from './JobOverviewTable.constants';
import DateTimeCell from '@commonComponents/Table/Cells/DateTimeCell';
import { secondsToDuration } from '@utils/date/timeConvertUtils';
import { apiHost } from '@constants';
import JobObjectsCell from '@commonComponents/Table/Cells/JobObjectsCell/JobObjectsCell';
import { orElseGet } from '@utils/checkUtils';

const JobOverviewTable = () => {
  const job = useStore((s) => s.adcm.job.job);
  const isLoading = useStore((s) => s.adcm.job.isLoading);

  return (
    <Table variant="quaternary" isLoading={isLoading} columns={columns}>
      {job && (
        <TableRow>
          <JobObjectsCell objects={job.objects} />
          <TableCell>{orElseGet(job.duration ?? 0, secondsToDuration)}</TableCell>
          <DateTimeCell value={job.startTime ?? undefined} />
          <DateTimeCell value={job.endTime ?? undefined} />
          <TableCell hasIconOnly>
            <a href={`${apiHost}/api/v2/tasks/${job.id}/logs/download/`} download="download">
              Download
            </a>
          </TableCell>
        </TableRow>
      )}
    </Table>
  );
};

export default JobOverviewTable;
