import ActionHostGroupsTableToolbar from '@commonComponents/ActionHostGroups/ActionHostGroupsTableToolbar/ActionHostGroupsTableToolbar';
import ActionHostGroupsTable from '@commonComponents/ActionHostGroups/ActionHostGroupsTable/ActionHostGroupsTable';
import CreateActionHostGroupDialog from '@commonComponents/ActionHostGroups/ActionHostGroupDialogs/CreateActionHostGroupDialog/CreateActionHostGroupDialog';
import DynamicActionDialog from '@commonComponents/DynamicActionDialog/DynamicActionDialog';
import EditActionHostGroupDialog from '@commonComponents/ActionHostGroups/ActionHostGroupDialogs/EditActionHostGroupDialog/EditActionHostGroupDialog';
import DeleteActionHostGroupDialog from '@commonComponents/ActionHostGroups/ActionHostGroupDialogs/DeleteActionHostGroupDialog/DeleteActionHostGroupDialog';
import { useServiceActionHostGroups } from './useServiceActionHostGroups';
import EntityDynamicActionWizardDialog from '@commonComponents/EntityWizard/EntityDynamicActionWizardDialog';

const ServiceActionHostGroups = () => {
  const {
    toolbarProps,
    tableProps,
    createDialogProps,
    dynamicActionDialogProps,
    editDialogProps,
    deleteDialogProps,
    wizardProps,
  } = useServiceActionHostGroups();

  return (
    <>
      <ActionHostGroupsTableToolbar {...toolbarProps} />
      <ActionHostGroupsTable {...tableProps} />
      <CreateActionHostGroupDialog {...createDialogProps} />
      {dynamicActionDialogProps && <DynamicActionDialog {...dynamicActionDialogProps} />}
      {editDialogProps && <EditActionHostGroupDialog {...editDialogProps} />}
      {deleteDialogProps && <DeleteActionHostGroupDialog {...deleteDialogProps} />}
      {wizardProps && <EntityDynamicActionWizardDialog {...wizardProps} />}
    </>
  );
};

export default ServiceActionHostGroups;
