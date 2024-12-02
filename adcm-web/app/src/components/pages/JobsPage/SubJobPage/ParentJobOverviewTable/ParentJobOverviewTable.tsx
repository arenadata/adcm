import { Table, TableRow, TableCell } from '@uikit';
import { useStore } from '@hooks';
import JobObjectsCell from '@commonComponents/Table/Cells/JobObjectsCell/JobObjectsCell';
import { columns } from '@pages/JobsPage/JobPage/JobOverviewTable/JobOverviewTable.constants';
import DateTimeCell from '@commonComponents/Table/Cells/DateTimeCell';
import { secondsToDuration } from '@utils/date/timeConvertUtils';
import { orElseGet } from '@utils/checkUtils';
import { apiHost } from '@constants';

const ParentJobOverviewTable = () => {
  const parentJob = useStore((s) => s.adcm.subJob.subJob?.parentTask);
  const isLoading = useStore((s) => s.adcm.subJob.isLoading);

  return (
    <Table variant="quaternary" isLoading={isLoading} columns={columns}>
      {parentJob && (
        <TableRow>
          <JobObjectsCell objects={parentJob.objects} />
          <TableCell>{orElseGet(parentJob.duration ?? 0, secondsToDuration)}</TableCell>
          <DateTimeCell value={parentJob.startTime ?? undefined} />
          <DateTimeCell value={parentJob.endTime ?? undefined} />
          <TableCell hasIconOnly>
            <a href={`${apiHost}/api/v2/tasks/${parentJob.id}/logs/download/`} download="download">
              Download
            </a>
          </TableCell>
        </TableRow>
      )}
    </Table>
  );
};

export default ParentJobOverviewTable;
