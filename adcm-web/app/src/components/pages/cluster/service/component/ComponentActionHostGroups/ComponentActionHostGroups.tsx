import ActionHostGroupsTableToolbar from '@commonComponents/ActionHostGroups/ActionHostGroupsTableToolbar/ActionHostGroupsTableToolbar';
import ActionHostGroupsTable from '@commonComponents/ActionHostGroups/ActionHostGroupsTable/ActionHostGroupsTable';
import CreateActionHostGroupDialog from '@commonComponents/ActionHostGroups/ActionHostGroupDialogs/CreateActionHostGroupDialog/CreateActionHostGroupDialog';
import DynamicActionDialog from '@commonComponents/DynamicActionDialog/DynamicActionDialog';
import EditActionHostGroupDialog from '@commonComponents/ActionHostGroups/ActionHostGroupDialogs/EditActionHostGroupDialog/EditActionHostGroupDialog';
import DeleteActionHostGroupDialog from '@commonComponents/ActionHostGroups/ActionHostGroupDialogs/DeleteActionHostGroupDialog/DeleteActionHostGroupDialog';
import { useComponentActionHostGroups } from './useComponentActionHostGroups';

const ComponentActionHostGroups = () => {
  const { toolbarProps, tableProps, createDialogProps, dynamicActionDialogProps, editDialogProps, deleteDialogProps } =
    useComponentActionHostGroups();

  return (
    <>
      <ActionHostGroupsTableToolbar {...toolbarProps} />
      <ActionHostGroupsTable {...tableProps} />
      <CreateActionHostGroupDialog {...createDialogProps} />
      {dynamicActionDialogProps && <DynamicActionDialog {...dynamicActionDialogProps} />}
      {editDialogProps && <EditActionHostGroupDialog {...editDialogProps} />}
      {deleteDialogProps && <DeleteActionHostGroupDialog {...deleteDialogProps} />}
    </>
  );
};

export default ComponentActionHostGroups;
