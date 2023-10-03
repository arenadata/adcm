import React from 'react';
import AccessManagerPolicyDeleteDialog from './AccessManagerPolicyDeleteDialog/AccessManagerPolicyDeleteDialog';
import AccessManagerPolicyAddDialog from '@pages/AccessManagerPage/AccessManagerPoliciesPage/Dialogs/AccessManagerPolicyAddDialog/AccessManagerPolicyAddDialog';

const AccessManagerPoliciesDialogs: React.FC = () => {
  return (
    <>
      <AccessManagerPolicyAddDialog />
      <AccessManagerPolicyDeleteDialog />
    </>
  );
};

export default AccessManagerPoliciesDialogs;
