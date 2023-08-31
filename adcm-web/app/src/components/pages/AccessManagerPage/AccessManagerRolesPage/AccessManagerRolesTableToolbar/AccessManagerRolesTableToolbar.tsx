import AccessManagerRolesTableFilters from './AccessManagerRolesTableFilters';
import { Button, ButtonGroup } from '@uikit';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';

const AccessManagerRolesTableToolbar = () => {
  return (
    <TableToolbar>
      <AccessManagerRolesTableFilters />
      <ButtonGroup>
        <Button>Create role</Button>
      </ButtonGroup>
    </TableToolbar>
  );
};

export default AccessManagerRolesTableToolbar;
