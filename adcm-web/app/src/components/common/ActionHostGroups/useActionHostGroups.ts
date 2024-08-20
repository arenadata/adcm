import { useStore, useDispatch } from '@hooks';
import {
  openCreateDialog,
  createActionHostGroupWithUpdate,
  closeCreateDialog,
  openEditDialog,
  updateActionHostGroupWithUpdate,
  closeEditDialog,
  openDeleteDialog,
  deleteActionHostGroupWithUpdate,
  closeDeleteDialog,
} from '@store/adcm/entityActionHostGroups/actionHostGroupsActionsSlice';
import {
  openDynamicActionDialog,
  closeDynamicActionDialog,
  runDynamicAction,
} from '@store/adcm/entityDynamicActions/dynamicActionsSlice';
import { setFilter, resetFilter } from '@store/adcm/entityActionHostGroups/actionHostGroupsTableSlice';
import type { AdcmActionHostGroupFormData } from '@commonComponents/ActionHostGroups/ActionHostGroupDialogs/ActionHostGroupDialogForm/useActionHostGroupDialogForm';
import type { ActionHostGroupsTableToolbarProps } from '@commonComponents/ActionHostGroups/ActionHostGroupsTableToolbar/ActionHostGroupsTableToolbar';
import type { ActionHostGroupsTableFiltersProps } from '@commonComponents/ActionHostGroups/ActionHostGroupsTableToolbar/ActionHostGroupsTableFilters';
import type { ActionHostGroupsTableProps } from '@commonComponents/ActionHostGroups/ActionHostGroupsTable/ActionHostGroupsTable';
import type { CreateActionHostGroupDialogProps } from '@commonComponents/ActionHostGroups/ActionHostGroupDialogs/CreateActionHostGroupDialog/CreateActionHostGroupDialog';
import type { DynamicActionDialogProps } from '@commonComponents/DynamicActionDialog/DynamicActionDialog';
import type { EditActionHostGroupDialogProps } from './ActionHostGroupDialogs/EditActionHostGroupDialog/EditActionHostGroupDialog';
import type { DeleteActionHostGroupDialogProps } from '@commonComponents/ActionHostGroups/ActionHostGroupDialogs/DeleteActionHostGroupDialog/DeleteActionHostGroupDialog';
import type { ActionHostGroupOwner, EntityArgs } from '@store/adcm/entityActionHostGroups/actionHostGroups.types';
import type { AdcmActionHostGroup, AdcmActionHostGroupsFilter, AdcmDynamicActionRunConfig } from '@models/adcm';
import { useRequestActionHostGroups } from './useRequestActionHostGroups';
import { isShowSpinner } from '@uikit/Table/Table.utils';

type UseActionHostGroupsResult<T extends ActionHostGroupOwner> = {
  entityArgs: EntityArgs<T>;
  toolbarProps: ActionHostGroupsTableToolbarProps & ActionHostGroupsTableFiltersProps;
  tableProps: ActionHostGroupsTableProps;
  createDialogProps: CreateActionHostGroupDialogProps;
  dynamicActionDialogProps?: DynamicActionDialogProps;
  editDialogProps?: EditActionHostGroupDialogProps;
  deleteDialogProps?: DeleteActionHostGroupDialogProps;
};

export const useActionHostGroups = <T extends ActionHostGroupOwner>(
  entityType: T,
  entityArgs: EntityArgs<T>,
): UseActionHostGroupsResult<T> => {
  const dispatch = useDispatch();

  useRequestActionHostGroups(entityType, entityArgs);

  const isActionHostGroupsLoading = useStore(({ adcm }) => isShowSpinner(adcm.actionHostGroups.loadState));
  const actionHostGroups = useStore(({ adcm }) => adcm.actionHostGroups.actionHostGroups);

  const runnableActionHostGroupId = useStore(({ adcm }) => adcm.dynamicActions.actionHostGroupId);
  const dynamicActions = useStore(({ adcm }) => adcm.dynamicActions.dynamicActions);
  const dynamicActionDetails = useStore(({ adcm }) => adcm.dynamicActions.actionDetails);

  const isCreateDialogOpen = useStore(({ adcm }) => adcm.actionHostGroupsActions.createDialog.isOpen);
  const allHostCandidates = useStore(
    ({ adcm }) => adcm.actionHostGroupsActions.createDialog.relatedData.hostCandidates,
  );
  const editableActionHostGroup = useStore(({ adcm }) => adcm.actionHostGroupsActions.editDialog.actionHostGroup);
  const actionHostGroupHostCandidates = useStore(
    ({ adcm }) => adcm.actionHostGroupsActions.editDialog.relatedData.hostCandidates,
  );
  const deletableActionHostGroup = useStore(({ adcm }) => adcm.actionHostGroupsActions.deleteDialog.actionHostGroup);
  const filter = useStore(({ adcm }) => adcm.actionHostGroupsTable.filter);

  // Create dialog

  const handleOpenCreateDialog = () => {
    dispatch(openCreateDialog({ entityType, entityArgs }));
  };

  const handleCreate = (formData: AdcmActionHostGroupFormData) => {
    dispatch(
      createActionHostGroupWithUpdate({
        entityType,
        entityArgs,
        actionHostGroup: {
          name: formData.name,
          description: formData.description,
        },
        hostIds: formData.hosts,
      }),
    );
  };

  const handleCloseCreateDialog = () => {
    dispatch(closeCreateDialog());
  };

  // Dynamic action dialog

  const handleOpenDynamicActionDialog = (actionHostGroup: AdcmActionHostGroup, actionId: number) => {
    dispatch(openDynamicActionDialog({ entityType, entityArgs, actionHostGroupId: actionHostGroup.id, actionId }));
  };

  const handleSubmitDynamicAction = (actionRunConfig: AdcmDynamicActionRunConfig) => {
    dispatch(
      runDynamicAction({
        entityType,
        entityArgs,
        actionHostGroupId: runnableActionHostGroupId!,
        actionId: dynamicActionDetails!.id,
        actionRunConfig,
      }),
    );
  };

  const handleCloseDynamicActionDialog = () => {
    dispatch(closeDynamicActionDialog());
  };

  // Edit dialog

  const handleOpenEditDialog = (actionHostGroup: AdcmActionHostGroup) => {
    dispatch(openEditDialog({ entityType, entityArgs, actionHostGroup }));
  };

  const handleEdit = (formData: AdcmActionHostGroupFormData) => {
    if (editableActionHostGroup) {
      dispatch(
        updateActionHostGroupWithUpdate({
          entityType,
          entityArgs,
          actionHostGroup: editableActionHostGroup,
          hostIds: formData.hosts,
        }),
      );
    }
  };

  const handleCloseEditDialog = () => {
    dispatch(closeEditDialog());
  };

  // Delete dialog

  const handleOpenDeleteDialog = (actionHostGroup: AdcmActionHostGroup) => {
    dispatch(openDeleteDialog({ actionHostGroup }));
  };

  const handleDelete = () => {
    if (deletableActionHostGroup) {
      dispatch(deleteActionHostGroupWithUpdate({ entityType, entityArgs, actionHostGroup: deletableActionHostGroup }));
    }
  };

  const handleCloseDeleteDialog = () => {
    dispatch(closeDeleteDialog());
  };

  // filters

  const handleFilterChange = (changes: Partial<AdcmActionHostGroupsFilter>) => {
    dispatch(setFilter(changes));
  };

  const handleFilterReset = () => {
    dispatch(resetFilter());
  };

  return {
    entityArgs,
    toolbarProps: {
      filter,
      onFilterChange: handleFilterChange,
      onFilterReset: handleFilterReset,
      onOpenCreateDialog: handleOpenCreateDialog,
    },
    tableProps: {
      actionHostGroups,
      dynamicActions,
      isLoading: isActionHostGroupsLoading,
      onOpenDynamicActionDialog: handleOpenDynamicActionDialog,
      onOpenEditDialog: handleOpenEditDialog,
      onOpenDeleteDialog: handleOpenDeleteDialog,
    },
    createDialogProps: {
      isOpen: isCreateDialogOpen,
      hostCandidates: allHostCandidates,
      onClose: handleCloseCreateDialog,
      onCreate: handleCreate,
    },
    dynamicActionDialogProps: dynamicActionDetails
      ? {
          actionDetails: dynamicActionDetails,
          clusterId: entityArgs.clusterId,
          onSubmit: handleSubmitDynamicAction,
          onCancel: handleCloseDynamicActionDialog,
        }
      : undefined,
    editDialogProps: editableActionHostGroup
      ? {
          isOpen: true,
          actionHostGroup: editableActionHostGroup,
          hostCandidates: [...actionHostGroupHostCandidates, ...editableActionHostGroup.hosts],
          onClose: handleCloseEditDialog,
          onEdit: handleEdit,
        }
      : undefined,
    deleteDialogProps: deletableActionHostGroup
      ? {
          isOpen: true,
          actionHostGroup: deletableActionHostGroup!,
          onDelete: handleDelete,
          onClose: handleCloseDeleteDialog,
        }
      : undefined,
  };
};
