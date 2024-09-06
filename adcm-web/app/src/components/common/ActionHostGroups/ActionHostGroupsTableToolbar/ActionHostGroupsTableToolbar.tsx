import { Button, ButtonGroup } from '@uikit';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import ActionHostGroupsTableFilters, { ActionHostGroupsTableFiltersProps } from './ActionHostGroupsTableFilters';

export interface ActionHostGroupsTableToolbarProps extends ActionHostGroupsTableFiltersProps {
  onOpenCreateDialog: () => void;
}

const ActionHostGroupsTableToolbar = ({ onOpenCreateDialog, ...filterProps }: ActionHostGroupsTableToolbarProps) => (
  <TableToolbar>
    <ActionHostGroupsTableFilters {...filterProps} />
    <ButtonGroup>
      <Button onClick={onOpenCreateDialog}>Create action host group</Button>
    </ButtonGroup>
  </TableToolbar>
);

export default ActionHostGroupsTableToolbar;
