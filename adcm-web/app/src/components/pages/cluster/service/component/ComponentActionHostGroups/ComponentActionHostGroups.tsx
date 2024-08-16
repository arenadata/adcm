import ActionHostGroupsTableToolbar from '@commonComponents/ActionHostGroups/ActionHostGroupsTableToolbar/ActionHostGroupsTableToolbar';
import ActionHostGroupsTable from '@commonComponents/ActionHostGroups/ActionHostGroupsTable/ActionHostGroupsTable';
import CreateActionHostGroupDialog from '@commonComponents/ActionHostGroups/ActionHostGroupDialogs/CreateActionHostGroupDialog/CreateActionHostGroupDialog';
import DynamicActionDialog from '@commonComponents/DynamicActionDialog/DynamicActionDialog';
import EditActionHostGroupDialog from '@commonComponents/ActionHostGroups/ActionHostGroupDialogs/EditActionHostGroupDialog/EditActionHostGroupDialog';
import DeleteActionHostGroupDialog from '@commonComponents/ActionHostGroups/ActionHostGroupDialogs/DeleteActionHostGroupDialog/DeleteActionHostGroupDialog';
import { useComponentActionHostGroups } from './useComponentActionHostGroups';
import { useDispatch, useStore } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import { useEffect } from 'react';

const ComponentActionHostGroups = () => {
  const { toolbarProps, tableProps, createDialogProps, dynamicActionDialogProps, editDialogProps, deleteDialogProps } =
    useComponentActionHostGroups();

  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const service = useStore(({ adcm }) => adcm.service.service);
  const component = useStore(({ adcm }) => adcm.serviceComponent.serviceComponent);

  useEffect(() => {
    if (cluster && service && component) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { href: `/clusters/${cluster.id}/services`, label: 'Services' },
          { href: `/clusters/${cluster.id}/services/${service.id}`, label: service.displayName },
          { href: `/clusters/${cluster.id}/services/${service.id}/components`, label: 'Components' },
          {
            href: `/clusters/${cluster.id}/services/${service.id}/components/${component.id}`,
            label: component.displayName,
          },
          { label: 'Action hosts groups' },
        ]),
      );
    }
  }, [cluster, service, component, dispatch]);

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
