import AccessManagerRoleCreateDialog from './AccessManagerRoleCreateDialog/AccessManagerRoleCreateDialog';
import AccessManagerRoleUpdateDialog from './AccessManagerRoleUpdateDialog/AccessManagerRoleUpdateDialog';
import AccessManagerRolesDeleteDialog from './AccessManagerRolesDeleteDialog/AccessManagerRolesDeleteDialog';

const AccessManagerRolesDialogs = () => {
  return (
    <>
      <AccessManagerRoleCreateDialog />
      <AccessManagerRolesDeleteDialog />
      <AccessManagerRoleUpdateDialog />
    </>
  );
};

export default AccessManagerRolesDialogs;
