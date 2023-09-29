import React, { useMemo, useState } from 'react';
import { Dialog, FormField, FormFieldsContainer, Input } from '@uikit';
import { useAccessManagerRoleCreateDialog } from './useAccessManagerRoleCreateDialog';
import s from './AccessManagerRoleCreateDialog.module.scss';
import AccessManagerRolesTableProducts from '../../AccessManagerRolesTable/AccessManagerRolesTableProducts/AccessManagerRolesTableProducts';
import ListTransfer from '@uikit/ListTransfer/ListTransfer';

const availablePermissionsPanel = {
  title: 'All available permissions',
  searchPlaceholder: 'Search permissions',
};
const selectedPermissionsPanel = {
  title: 'Selected permissions',
  searchPlaceholder: 'Search objects',
  actionButtonLabel: 'Remove selected',
};

const AccessManagerRoleCreateDialog = () => {
  const {
    isOpen,
    isValid,
    formData,
    relatedData: { allPermissions, products },
    onCreate,
    onClose,
    onChangeFormData,
    errors,
  } = useAccessManagerRoleCreateDialog();

  const [productsSelected, setProductsSelected] = useState(products);

  const allPermissionsByProducts = useMemo(() => {
    return allPermissions
      .filter((role) => role.categories.find((cat) => productsSelected.includes(cat)) || role.isAnyCategory)
      .map((permission) => {
        return {
          key: permission.id,
          label: permission.displayName,
        };
      });
  }, [allPermissions, productsSelected]);

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ displayName: event.target.value });
  };

  const handleDescriptionChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ description: event.target.value });
  };

  const handleSelectProducts = (value: string[]) => {
    setProductsSelected(value);
  };

  const handleChangeSelectedPermissions = (permissionsIds: Set<number>) => {
    onChangeFormData({ children: permissionsIds });
  };

  return (
    <Dialog
      title="Create role"
      actionButtonLabel="Create"
      isOpen={isOpen}
      onOpenChange={onClose}
      onAction={onCreate}
      isActionDisabled={!isValid}
      isDialogControlsOnTop
      width="100%"
      height="100%"
    >
      <FormFieldsContainer className={s.roleCreateDialog}>
        <div className={s.roleCreateDialog__column}>
          <FormField label="Role name" className={s.roleCreateDialog__name} error={errors.displayName}>
            <Input
              value={formData.displayName}
              type="text"
              onChange={handleNameChange}
              placeholder="Enter name"
              autoComplete="off"
            />
          </FormField>
          <FormField label="Description" className={s.roleCreateDialog__description}>
            <Input
              value={formData.description}
              type="text"
              onChange={handleDescriptionChange}
              placeholder="Enter short description"
              autoComplete="off"
            />
          </FormField>

          <div>
            <div className={s.roleCreateDialog__productsLabel}>Product filter</div>
            <AccessManagerRolesTableProducts onSelect={handleSelectProducts} />
          </div>
        </div>

        <ListTransfer
          srcList={allPermissionsByProducts}
          destKeys={formData.children}
          onChangeDest={handleChangeSelectedPermissions}
          srcOptions={availablePermissionsPanel}
          destOptions={selectedPermissionsPanel}
          destError={errors.children}
        />
      </FormFieldsContainer>
    </Dialog>
  );
};

export default AccessManagerRoleCreateDialog;
