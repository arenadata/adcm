import type React from 'react';
import AccessManagerPolicyCreateDialog from './AccessManagerPolicyCreateDialog/AccessManagerPolicyCreateDialog';
import AccessManagerPolicyUpdateDialog from './AccessManagerPolicyUpdateDialog/AccessManagerPolicyUpdateDialog';
import AccessManagerPolicyDeleteDialog from './AccessManagerPolicyDeleteDialog/AccessManagerPolicyDeleteDialog';

const AccessManagerPoliciesDialogs: React.FC = () => {
  return (
    <>
      <AccessManagerPolicyCreateDialog />
      <AccessManagerPolicyUpdateDialog />
      <AccessManagerPolicyDeleteDialog />
    </>
  );
};

export default AccessManagerPoliciesDialogs;
