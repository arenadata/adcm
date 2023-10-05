import React, { useMemo, useState } from 'react';
import { FormField, FormFieldsContainer, Input } from '@uikit';
import s from './AccessManagerRoleDialogForm.module.scss';
import AccessManagerRolesTableProducts from '../../AccessManagerRolesTable/AccessManagerRolesTableProducts/AccessManagerRolesTableProducts';
import ListTransfer from '@uikit/ListTransfer/ListTransfer';
import { AdcmRoleFormData, useAccessManagerRoleDialogForm } from './useAccessManagerRoleDialogForm';

const availablePermissionsPanel = {
  title: 'All available permissions',
  searchPlaceholder: 'Search permissions',
};
const selectedPermissionsPanel = {
  title: 'Selected permissions',
  searchPlaceholder: 'Search permissions',
  actionButtonLabel: 'Remove selected',
};

interface AccessManagerRoleDialogFormProps {
  onChangeFormData: (prop: Partial<AdcmRoleFormData>) => void;
  formData: AdcmRoleFormData;
  errors: Partial<Record<keyof AdcmRoleFormData, string | undefined>>;
}

const AccessManagerRoleDialogForm: React.FC<AccessManagerRoleDialogFormProps> = ({
  formData,
  onChangeFormData,
  errors,
}) => {
  const {
    relatedData: { allPermissions, products },
  } = useAccessManagerRoleDialogForm();

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
    <FormFieldsContainer className={s.roleDialogForm}>
      <div className={s.roleDialogForm__column}>
        <FormField label="Role name" className={s.roleDialogForm__name} error={errors.displayName}>
          <Input
            value={formData.displayName}
            type="text"
            onChange={handleNameChange}
            placeholder="Enter name"
            autoComplete="off"
          />
        </FormField>
        <FormField label="Description" className={s.roleDialogForm__description}>
          <Input
            value={formData.description}
            type="text"
            onChange={handleDescriptionChange}
            placeholder="Enter short description"
            autoComplete="off"
          />
        </FormField>

        <div>
          <div className={s.roleDialogForm__productsLabel}>Product filter</div>
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
  );
};

export default AccessManagerRoleDialogForm;
