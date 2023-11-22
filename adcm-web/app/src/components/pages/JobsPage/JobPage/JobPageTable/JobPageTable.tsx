import { Table, TableRow, TableCell } from '@uikit';
import { useStore } from '@hooks';
import { columns } from './JobPageTable.constants';
import DateTimeCell from '@commonComponents/Table/Cells/DateTimeCell';
import { secondsToDuration } from '@utils/date/timeConvertUtils';
import { apiHost } from '@constants';
import JobObjectsCell from '@commonComponents/Table/Cells/JobObjectsCell/JobObjectsCell';

const JobPageTable = () => {
  const task = useStore((s) => s.adcm.jobs.task);
  const isLoading = useStore((s) => s.adcm.jobs.isLoading);

  const downloadLink = `${apiHost}/api/v2/tasks/${task.id}/logs/download/`;

  return (
    <Table variant="quaternary" isLoading={isLoading} columns={columns}>
      <TableRow>
        <JobObjectsCell objects={task.objects} />
        <TableCell>{secondsToDuration(task.duration)}</TableCell>
        <DateTimeCell value={task.startTime} />
        <DateTimeCell value={task.endTime} />
        <TableCell hasIconOnly>
          <a href={downloadLink} download="download">
            Download
          </a>
        </TableCell>
      </TableRow>
    </Table>
  );
};

export default JobPageTable;
