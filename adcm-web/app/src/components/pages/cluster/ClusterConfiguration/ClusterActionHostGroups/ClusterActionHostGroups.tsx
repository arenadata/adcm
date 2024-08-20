import ActionHostGroupsTableToolbar from '@commonComponents/ActionHostGroups/ActionHostGroupsTableToolbar/ActionHostGroupsTableToolbar';
import ActionHostGroupsTable from '@commonComponents/ActionHostGroups/ActionHostGroupsTable/ActionHostGroupsTable';
import CreateActionHostGroupDialog from '@commonComponents/ActionHostGroups/ActionHostGroupDialogs/CreateActionHostGroupDialog/CreateActionHostGroupDialog';
import DynamicActionDialog from '@commonComponents/DynamicActionDialog/DynamicActionDialog';
import EditActionHostGroupDialog from '@commonComponents/ActionHostGroups/ActionHostGroupDialogs/EditActionHostGroupDialog/EditActionHostGroupDialog';
import DeleteActionHostGroupDialog from '@commonComponents/ActionHostGroups/ActionHostGroupDialogs/DeleteActionHostGroupDialog/DeleteActionHostGroupDialog';
import { useClusterActionHostGroups } from './useClusterActionHostGroups';
import { useDispatch, useStore } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import { useEffect } from 'react';

const ClusterActionHostGroups = () => {
  const { toolbarProps, tableProps, createDialogProps, dynamicActionDialogProps, editDialogProps, deleteDialogProps } =
    useClusterActionHostGroups();

  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  const dispatch = useDispatch();

  useEffect(() => {
    if (cluster) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { href: `/clusters/${cluster.id}/configuration`, label: 'Configuration' },
          { label: 'Action hosts groups' },
        ]),
      );
    }
  }, [cluster, dispatch]);

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

export default ClusterActionHostGroups;
