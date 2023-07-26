import HostProviderTableFilters from './HostProviderTableFilters';
import { ButtonGroup } from '@uikit';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import HostProviderCreateButton from './HostProviderUploadButton/HostProviderCreateButton';

const HostProviderTableToolbar = () => (
  <TableToolbar>
    <HostProviderTableFilters />
    <ButtonGroup>
      <HostProviderCreateButton />
    </ButtonGroup>
  </TableToolbar>
);

export default HostProviderTableToolbar;
