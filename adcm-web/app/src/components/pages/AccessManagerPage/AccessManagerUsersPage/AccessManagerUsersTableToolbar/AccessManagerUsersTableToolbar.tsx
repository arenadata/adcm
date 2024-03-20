import AccessManagerUsersTableFilters from './AccessManagerUsersTableFilters';
import { ButtonGroup } from '@uikit';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import AccessManagerUsersDeleteButton from './AccessManagerUsersDeleteButton/AccessManagerUsersDeleteButton';
import AccessManagerUsersBlockUnblockButtons from './AccessManagerUsersBlockUnblockButtons';
import AccessManagerUsersCreateButton from './AccessManagerUsersCreateButton';

const AccessManagerUsersTableToolbar = () => {
  return (
    <TableToolbar>
      <AccessManagerUsersTableFilters />
      <ButtonGroup>
        <AccessManagerUsersBlockUnblockButtons />
        <AccessManagerUsersDeleteButton />
        <AccessManagerUsersCreateButton />
      </ButtonGroup>
    </TableToolbar>
  );
};

export default AccessManagerUsersTableToolbar;
