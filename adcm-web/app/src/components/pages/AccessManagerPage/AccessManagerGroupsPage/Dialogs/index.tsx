import AccessManagerGroupsCreateGroupDialog from './AccessManagerGroupsCreateGroupDialog/AccessManagerGroupsCreateGroupDialog';
import AccessManagerGroupsDeleteDialog from './AccessManagerGroupsDeleteDialog/AccessManagerGroupsDeleteDialog';
import AccessManagerGroupsUpdateGroupDialog from './AccessManagerGroupsUpdateGroupDialog/AccessManagerGroupsUpdateGroupDialog';

const AccessManagerGroupsDialogs = () => {
  return (
    <>
      <AccessManagerGroupsDeleteDialog />
      <AccessManagerGroupsCreateGroupDialog />
      <AccessManagerGroupsUpdateGroupDialog />
    </>
  );
};

export default AccessManagerGroupsDialogs;
