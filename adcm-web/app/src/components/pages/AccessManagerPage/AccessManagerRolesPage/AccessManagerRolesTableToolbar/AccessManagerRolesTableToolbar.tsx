import AccessManagerRolesTableFilters from './AccessManagerRolesTableFilters';
import { ButtonGroup } from '@uikit';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import AccessManagerRolesCreateButton from './AccessManagerRolesCreateButton';

const AccessManagerRolesTableToolbar = () => {
  return (
    <TableToolbar>
      <AccessManagerRolesTableFilters />
      <ButtonGroup>
        <AccessManagerRolesCreateButton />
      </ButtonGroup>
    </TableToolbar>
  );
};

export default AccessManagerRolesTableToolbar;
