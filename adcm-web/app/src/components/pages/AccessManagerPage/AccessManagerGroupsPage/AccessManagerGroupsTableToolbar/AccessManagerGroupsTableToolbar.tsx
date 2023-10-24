import AccessManagerGroupsTableFilters from './AccessManagerGroupsTableFilters';
import { ButtonGroup } from '@uikit';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import AccessManagerGroupsDeleteButton from './AccessManagerGroupsDeleteButton/AccessManagerGroupsDeleteButton';
import RbacGroupCreateButton from './RbacGroupCreateButton/RbacGroupCreateButton';

const AccessManagerGroupsTableToolbar = () => {
  return (
    <TableToolbar>
      <AccessManagerGroupsTableFilters />
      <ButtonGroup>
        <AccessManagerGroupsDeleteButton />
        <RbacGroupCreateButton />
      </ButtonGroup>
    </TableToolbar>
  );
};

export default AccessManagerGroupsTableToolbar;
