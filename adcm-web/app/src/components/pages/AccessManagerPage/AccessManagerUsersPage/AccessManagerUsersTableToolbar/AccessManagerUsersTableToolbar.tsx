import AccessManagerUsersTableFilters from './AccessManagerUsersTableFilters';
import { Button, ButtonGroup } from '@uikit';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import AccessManagerUsersDeleteButton from './AccessManagerUsersDeleteButton/AccessManagerUsersDeleteButton';
import AccessManagerUsersBlockUnblockButtons from './AccessManagerUsersBlockUnblockButton';

const AccessManagerUsersTableToolbar = () => {
  return (
    <TableToolbar>
      <AccessManagerUsersTableFilters />
      <ButtonGroup>
        <AccessManagerUsersBlockUnblockButtons />
        <AccessManagerUsersDeleteButton />
        <Button>Create user</Button>
      </ButtonGroup>
    </TableToolbar>
  );
};

export default AccessManagerUsersTableToolbar;
