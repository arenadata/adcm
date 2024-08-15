import { Button, ButtonGroup } from '@uikit';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import ClusterActionHostGroupsTableFilters, {
  ClusterActionHostGroupsTableFiltersProps,
} from './ActionHostGroupsTableFilters';

export interface ClusterActionHostGroupsTableToolbarProps extends ClusterActionHostGroupsTableFiltersProps {
  onOpenCreateDialog: () => void;
}

const ClusterActionHostGroupsTableToolbar = ({
  onOpenCreateDialog,
  ...filterProps
}: ClusterActionHostGroupsTableToolbarProps) => (
  <TableToolbar>
    <ClusterActionHostGroupsTableFilters {...filterProps} />
    <ButtonGroup>
      <Button onClick={onOpenCreateDialog}>Create action hosts group</Button>
    </ButtonGroup>
  </TableToolbar>
);

export default ClusterActionHostGroupsTableToolbar;
