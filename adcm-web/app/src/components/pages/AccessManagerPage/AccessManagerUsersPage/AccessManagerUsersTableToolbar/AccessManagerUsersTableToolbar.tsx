import AccessManagerUsersTableFilters from './AccessManagerUsersTableFilters';
import { Button, ButtonGroup } from '@uikit';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import AccessManagerUsersDeleteButton from './AccessManagerUsersDeleteButton/AccessManagerUsersDeleteButton';
import { useStore } from '@hooks';

const AccessManagerUsersTableToolbar = () => {
  const selectedItemsIds = useStore(({ adcm }) => adcm.users.selectedItemsIds);
  const isSelectedSomeRows = selectedItemsIds.length > 0;

  return (
    <TableToolbar>
      <AccessManagerUsersTableFilters />
      <ButtonGroup>
        <Button variant="secondary" disabled={!isSelectedSomeRows}>
          Block
        </Button>
        <Button variant="secondary" disabled={!isSelectedSomeRows}>
          Unblock
        </Button>
        <AccessManagerUsersDeleteButton />
        <Button>Create user</Button>
      </ButtonGroup>
    </TableToolbar>
  );
};

export default AccessManagerUsersTableToolbar;
