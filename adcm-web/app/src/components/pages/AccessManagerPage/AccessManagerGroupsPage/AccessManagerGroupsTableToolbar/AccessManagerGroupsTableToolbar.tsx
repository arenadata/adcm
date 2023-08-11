import AccessManagerGroupsTableFilters from './AccessManagerGroupsTableFilters';
import { Button, ButtonGroup } from '@uikit';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import AccessManagerGroupsDeleteButton from './AccessManagerGroupsDeleteButton/AccessManagerGroupsDeleteButton';

const AccessManagerGroupsTableToolbar = () => {
  return (
    <TableToolbar>
      <AccessManagerGroupsTableFilters />
      <ButtonGroup>
        <AccessManagerGroupsDeleteButton />
        <Button>Create group</Button>
      </ButtonGroup>
    </TableToolbar>
  );
};

export default AccessManagerGroupsTableToolbar;
