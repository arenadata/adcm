import { useDispatch, useStore } from '@hooks';
import { DialogV2, FormFieldsContainer } from '@uikit';
import { closeCreateDialog } from '@store/adcm/cluster/hosts/hostsActionsSlice';
import MultiSelectPanel from '@uikit/Select/MultiSelect/MultiSelectPanel/MultiSelectPanel';
import { useCreateClusterHostsForm } from '@pages/cluster/ClusterHosts/ClusterHostsActionsDialogs/AddClusterHostsDialog/useAddClusterHostsDialog';
import { useEffect } from 'react';

const AddClusterHostsDialog = () => {
  const dispatch = useDispatch();

  const isOpenDialog = useStore(({ adcm }) => adcm.clusterHostsActions.createDialog.isOpen);

  const {
    formData,
    submit,
    resetForm,
    onChangeFormData,
    loadRelatedData,
    relatedData: { hostsOptions },
    isValid,
  } = useCreateClusterHostsForm();

  useEffect(() => {
    resetForm();
    if (isOpenDialog) {
      loadRelatedData();
    }
  }, [isOpenDialog, resetForm, loadRelatedData]);

  const handleClusterHostsChange = (value: number[]) => {
    onChangeFormData({ selectedHostIds: value });
  };

  const handleCloseDialog = () => {
    dispatch(closeCreateDialog());
  };

  return (
    isOpenDialog && (
      <DialogV2
        title="Add hosts"
        onAction={submit}
        onCancel={handleCloseDialog}
        isActionDisabled={!isValid}
        actionButtonLabel="Add"
      >
        <FormFieldsContainer>
          {hostsOptions.length > 0 && (
            <MultiSelectPanel
              options={hostsOptions}
              value={formData.selectedHostIds}
              onChange={handleClusterHostsChange}
              checkAllLabel="All hosts"
              searchPlaceholder="Search hosts"
              isSearchable={true}
            />
          )}
          {hostsOptions.length === 0 && <div>No available hosts found</div>}
        </FormFieldsContainer>
      </DialogV2>
    )
  );
};

export default AddClusterHostsDialog;
