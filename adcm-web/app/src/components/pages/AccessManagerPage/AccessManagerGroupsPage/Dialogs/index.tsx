import AccessManagerGroupsCreateGroupDialog from './AccessManagerGroupsCreateGroupDialog/AccessManagerGroupsCreateGroupDialog';
import AccessManagerGroupsDeleteDialog from './AccessManagerGroupsDeleteDialog/AccessManagerGroupsDeleteDialog';

const AccessManagerGroupsDialogs = () => {
  return (
    <>
      <AccessManagerGroupsDeleteDialog />
      <AccessManagerGroupsCreateGroupDialog />
    </>
  );
};

export default AccessManagerGroupsDialogs;
