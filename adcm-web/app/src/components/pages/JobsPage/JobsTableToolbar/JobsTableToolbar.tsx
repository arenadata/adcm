import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import JobsTableFilters from './JobsTableFilters';

const JobsTableToolbar = () => {
  return (
    <TableToolbar>
      <JobsTableFilters />
    </TableToolbar>
  );
};

export default JobsTableToolbar;
