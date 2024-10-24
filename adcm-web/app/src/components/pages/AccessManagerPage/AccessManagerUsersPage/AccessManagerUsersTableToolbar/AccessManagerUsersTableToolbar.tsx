import AccessManagerUsersTableFilters from './AccessManagerUsersTableFilters';
import { ButtonGroup } from '@uikit';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import AccessManagerUsersDeleteButton from './AccessManagerUsersDeleteButton/AccessManagerUsersDeleteButton';
import AccessManagerUsersCreateButton from './AccessManagerUsersCreateButton';
import AccessManagerUsersTableBlockButton from './AccessManagerUsersTableBlockButton/AccessManagerUsersTableBlockButton';
import AccessManagerUsersTableUnblockButton from './AccessManagerUsersTableUnblockButton/AccessManagerUsersTableUnblockButton';

const AccessManagerUsersTableToolbar = () => {
  return (
    <TableToolbar>
      <AccessManagerUsersTableFilters />
      <ButtonGroup>
        <AccessManagerUsersTableBlockButton />
        <AccessManagerUsersTableUnblockButton />
        <AccessManagerUsersDeleteButton />
        <AccessManagerUsersCreateButton />
      </ButtonGroup>
    </TableToolbar>
  );
};

export default AccessManagerUsersTableToolbar;
