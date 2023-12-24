import AccessManagerUsersDeleteDialog from './AccessManagerUsersDeleteDialog/AccessManagerUsersDeleteDialog';
import AccessManagerUsersUnblockDialog from './AccessManagerUsersUnblockDialog/AccessManagerUsersUnblockDialog';
import RbacUserCreateDialog from './RbacUserCreateDialog/RbacUserCreateDialog';
import RbacUserUpdateDialog from './RbacUserUpdateDialog/RbacUserUpdateDialog';

const AccessManagerUsersDialogs = () => {
  return (
    <>
      <AccessManagerUsersDeleteDialog />
      <AccessManagerUsersUnblockDialog />
      <RbacUserCreateDialog />
      <RbacUserUpdateDialog />
    </>
  );
};

export default AccessManagerUsersDialogs;
