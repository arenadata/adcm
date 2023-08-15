import { useDispatch, useStore } from '@hooks';
import { closeDeleteDialog, deletePolicyWithUpdate } from '@store/adcm/policies/policiesActionsSlice';
import { Dialog } from '@uikit';
import React from 'react';

const AccessManagerPolicyDeleteDialog: React.FC = () => {
  const dispatch = useDispatch();

  const deletableId = useStore(({ adcm }) => adcm.policiesActions.deleteDialog.id);
  const policies = useStore(({ adcm }) => adcm.policies.policies);

  const isOpen = deletableId !== null;
  const policyName = policies.find(({ id }) => id === deletableId)?.name;

  const handleCloseConfirm = () => {
    dispatch(closeDeleteDialog());
  };

  const handleConfirmDialog = () => {
    if (deletableId === null) return;

    dispatch(deletePolicyWithUpdate(deletableId));
  };

  return (
    <>
      <Dialog
        //
        isOpen={isOpen}
        onOpenChange={handleCloseConfirm}
        title={`Delete "${policyName}" policy`}
        onAction={handleConfirmDialog}
        actionButtonLabel="Delete"
      >
        The policy will be deleted. Are you sure?
      </Dialog>
    </>
  );
};

export default AccessManagerPolicyDeleteDialog;
