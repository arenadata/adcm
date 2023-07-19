import BundlesTableFilters from './BundlesTableFilters';
import { ButtonGroup } from '@uikit';
import TableToolbar from '@commonComponents/Table/TableToolbar/TableToolbar';
import BundlesDeleteButton from './BundlesDeleteButton/BundlesDeleteButton';
import BundleUploadButton from './BundleUploadButton/BundleUploadButton';

const BundlesTableToolbar = () => (
  <TableToolbar>
    <BundlesTableFilters />
    <ButtonGroup>
      <BundlesDeleteButton />
      <BundleUploadButton />
    </ButtonGroup>
  </TableToolbar>
);

export default BundlesTableToolbar;
