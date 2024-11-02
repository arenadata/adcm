import { useDispatch, useStore } from '@hooks';
import { closeDeleteDialog, deletePolicyWithUpdate } from '@store/adcm/policies/policiesActionsSlice';
import { Dialog } from '@uikit';
import React from 'react';

const AccessManagerPolicyDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const policy = useStore(({ adcm }) => adcm.policiesActions.deleteDialog?.policy);

  const isOpen = policy !== null;

  const handleCloseConfirm = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    if (policy === null) return;

    dispatch(deletePolicyWithUpdate(policy.id));
  };

  return (
    <Dialog
      //
      isOpen={isOpen}
      onOpenChange={handleCloseConfirm}
      title={`Delete "${policy?.name}" policy`}
      onAction={handleConfirmDialog}
      actionButtonLabel="Delete"
    >
      The policy will be deleted.
    </Dialog>
  );
};

export default AccessManagerPolicyDeleteDialog;
