import AccessManagerUsersBlockDialog from './AccessManagerUsersBlockDialog/AccessManagerUsersBlockDialog';
import AccessManagerUsersDeleteDialog from './AccessManagerUsersDeleteDialog/AccessManagerUsersDeleteDialog';
import AccessManagerUsersUnblockDialog from './AccessManagerUsersUnblockDialog/AccessManagerUsersUnblockDialog';
import RbacUserCreateDialog from './RbacUserCreateDialog/RbacUserCreateDialog';
import RbacUserUpdateDialog from './RbacUserUpdateDialog/RbacUserUpdateDialog';

const AccessManagerUsersDialogs = () => {
  return (
    <>
      <AccessManagerUsersDeleteDialog />
      <AccessManagerUsersUnblockDialog />
      <AccessManagerUsersBlockDialog />
      <RbacUserCreateDialog />
      <RbacUserUpdateDialog />
    </>
  );
};

export default AccessManagerUsersDialogs;
