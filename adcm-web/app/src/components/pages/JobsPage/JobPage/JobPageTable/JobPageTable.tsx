import { Link } from 'react-router-dom';
import { Table, TableRow, TableCell } from '@uikit';
import { useStore } from '@hooks';
import { columns } from './JobPageTable.constants';
import { linkByObjectTypeMap } from '@pages/JobsPage/JobsTable/JobsTable.constants';
import DateTimeCell from '@commonComponents/Table/Cells/DateTimeCell';
import { secondsToDuration } from '@utils/date/timeConvertUtils';
import { apiHost } from '@constants';

const JobPageTable = () => {
  const task = useStore((s) => s.adcm.jobs.task);
  const isLoading = useStore((s) => s.adcm.jobs.isLoading);

  const downloadLink = `${apiHost}/api/v2/tasks/${task.id}/logs/download/`;

  return (
    <Table variant="quaternary" isLoading={isLoading} columns={columns}>
      {task.objects?.map((object) => {
        return (
          <TableRow key={object.id}>
            <TableCell>
              <Link to={`/${linkByObjectTypeMap[object.type]}/${object.id}/`}>{object.name}</Link>
            </TableCell>
            <TableCell>{secondsToDuration(task.duration)}</TableCell>
            <DateTimeCell value={task.startTime} />
            <DateTimeCell value={task.startTime} />
            <TableCell hasIconOnly align="center">
              <Link to={downloadLink} download="download">
                Download
              </Link>
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};

export default JobPageTable;
