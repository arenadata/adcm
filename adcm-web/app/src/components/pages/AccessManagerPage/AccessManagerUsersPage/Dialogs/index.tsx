import AccessManagerUsersDeleteDialog from './AccessManagerUsersDeleteDialog/AccessManagerUsersDeleteDialog';
import RbacUserCreateDialog from './RbacUserCreateDialog/RbacUserCreateDialog';
import RbacUserUpdateDialog from './RbacUserUpdateDialog/RbacUserUpdateDialog';

const AccessManagerUsersDialogs = () => {
  return (
    <>
      <AccessManagerUsersDeleteDialog />
      <RbacUserCreateDialog />
      <RbacUserUpdateDialog />
    </>
  );
};

export default AccessManagerUsersDialogs;
