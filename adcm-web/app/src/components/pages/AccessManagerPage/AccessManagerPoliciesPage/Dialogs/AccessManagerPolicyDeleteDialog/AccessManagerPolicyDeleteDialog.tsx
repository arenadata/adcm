import { useDispatch, useStore } from '@hooks';
import { closeDeleteDialog, deletePolicyWithUpdate } from '@store/adcm/policies/policiesActionsSlice';
import { DialogV2 } from '@uikit';
import type React from 'react';

const AccessManagerPolicyDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const policy = useStore(({ adcm }) => adcm.policiesActions.deleteDialog?.policy);

  if (policy === null) return;

  const handleCloseConfirm = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    if (policy === null) return;

    dispatch(deletePolicyWithUpdate(policy.id));
  };

  return (
    <DialogV2
      //
      title={`Delete "${policy?.name}" policy`}
      onAction={handleConfirmDialog}
      onCancel={handleCloseConfirm}
      actionButtonLabel="Delete"
    >
      The policy will be deleted.
    </DialogV2>
  );
};

export default AccessManagerPolicyDeleteDialog;
