import { Link, generatePath } from 'react-router-dom';
import { Table, TableRow, TableCell } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { columns } from './JobPageTable.constants';
import { downloadTaskLog } from '@store/adcm/jobs/jobsActionsSlice';
import { linkByObjectTypeMap } from '@pages/JobsPage/JobsTable/JobsTable.constants';
import DateTimeCell from '@commonComponents/Table/Cells/DateTimeCell';
import { secondsToDuration } from '@utils/date/timeConvertUtils';

const JobPageTable = () => {
  const dispatch = useDispatch();
  const task = useStore((s) => s.adcm.jobs.task);
  const isLoading = useStore((s) => s.adcm.jobs.isLoading);

  const handleDownloadClick = (id: number) => () => {
    dispatch(downloadTaskLog(id));
  };

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
              <Link to={generatePath('/jobs/:jobId', { jobId: task.id + '' })} onClick={handleDownloadClick(task.id)}>
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
