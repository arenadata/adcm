import React, { useMemo, useState } from 'react';
import { useStore } from '@hooks';
import { AdcmRole } from '@models/adcm';
import cn from 'classnames';
import {
  Dialog,
  Checkbox,
  FormField,
  FormFieldsContainer,
  Input,
  SearchInput,
  Tag,
  CheckAll,
  IconButton,
  Tags,
} from '@uikit';
import { useAccessManagerRoleCreateDialog } from './useAccessManagerRoleCreateDialog';
import CustomDialogControls from '@commonComponents/Dialog/CustomDialogControls/CustomDialogControls';
import s from './AccessManagerRoleCreateDialog.module.scss';
import AccessManagerRolesTableProducts from '../../AccessManagerRolesTable/AccessManagerRolesTableProducts/AccessManagerRolesTableProducts';

const AccessManagerRoleCreateDialog = () => {
  const { isCreateDialogOpened, formData, onCreate, onClose, onChangeFormData } = useAccessManagerRoleCreateDialog();

  const products = useStore((s) => s.adcm.roles.relatedData.categories);
  const allPermissions = useStore((s) => s.adcm.rolesActions.relatedData.allRoles);

  const [productsSelected, setProductsSelected] = useState(products);
  const [allTextEntered, setAllTextEntered] = useState('');
  const [selectedTextEntered, setSelectedTextEntered] = useState('');

  const [allPermissionsSelected, setAllPermissionsSelected] = useState<AdcmRole[]>([]);
  const [selectedPermissionsSelected, setSelectedPermissionsSelected] = useState<AdcmRole[]>([]);

  const allPermissionsFiltered = useMemo(() => {
    return allPermissions
      .filter((role) => role.categories.find((cat) => productsSelected.includes(cat)) || role.isAnyCategory)
      .filter((role) => role.displayName.toLowerCase().includes(allTextEntered.toLowerCase()));
  }, [allPermissions, productsSelected, allTextEntered]);

  const selectedPermissionsFiltered = useMemo(() => {
    return allPermissionsSelected
      .filter((role) => role.categories.find((cat) => productsSelected.includes(cat)) || role.isAnyCategory)
      .filter((role) => role.displayName.toLowerCase().includes(selectedTextEntered.toLowerCase()));
  }, [allPermissionsSelected, productsSelected, selectedTextEntered]);

  const dialogControls = <CustomDialogControls actionButtonLabel="Create" onCancel={onClose} onAction={onCreate} />;

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ displayName: event.target.value });
  };

  const handleDescriptionChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ description: event.target.value });
  };

  const handleAllRoleNameFilter = (event: React.ChangeEvent<HTMLInputElement>) => {
    setAllTextEntered(event.target.value);
  };

  const handleSelectedRoleNameFilter = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSelectedTextEntered(event.target.value);
  };

  const handleCheckAllClick = (value: string[]) => {
    setProductsSelected(value);
  };

  const handleCheckAllPermissionsClick = (value: AdcmRole[]) => {
    setAllPermissionsSelected(value);
  };

  const handleCheckSelectedPermissionsClick = (value: AdcmRole[]) => {
    setSelectedPermissionsSelected(value);
  };

  const getHandlerCheckAllPermissionClick = (role: AdcmRole) => (event: React.ChangeEvent<HTMLInputElement>) => {
    const result = event.target.checked
      ? [...allPermissionsSelected, role]
      : allPermissionsSelected.filter((p) => p.id !== role.id);
    setAllPermissionsSelected(result);
  };

  const getHandlerCheckSelectedPermissionClick = (role: AdcmRole) => (event: React.ChangeEvent<HTMLInputElement>) => {
    const result = event.target.checked
      ? [...selectedPermissionsSelected, role]
      : selectedPermissionsSelected.filter((p) => p.id !== role.id);
    setSelectedPermissionsSelected(result);
    onChangeFormData({ children: result.map((p) => p.id) });
  };

  const getHandlerDeleteSelectedPermissionClick = (role: AdcmRole) => () => {
    setAllPermissionsSelected(allPermissionsSelected.filter((p) => p.id !== role.id));
    const result = selectedPermissionsSelected.filter((p) => p.id !== role.id);
    setSelectedPermissionsSelected(result);
    onChangeFormData({ children: result.map((p) => p.id) });
  };

  return (
    <Dialog
      title="Create role"
      actionButtonLabel="Create"
      isOpen={isCreateDialogOpened}
      onOpenChange={onClose}
      onAction={onCreate}
      dialogControls={dialogControls}
      dialogControlsOnTop={true}
      width="100%"
      height="100%"
    >
      <FormFieldsContainer className={s.roleCreateDialog}>
        <FormField label="Role name" className={s.roleCreateDialog__name}>
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
        <FormField label="Product filter" className={s.roleCreateDialog__products}>
          <AccessManagerRolesTableProducts onSelect={handleCheckAllClick} />
        </FormField>
        <FormField label="All available permissions" className={s.roleCreateDialog__allPermissions}>
          <>
            <SearchInput placeholder="Search permissions" value={allTextEntered} onChange={handleAllRoleNameFilter} />
            <CheckAll
              allList={allPermissions}
              selectedValues={allPermissionsSelected}
              onChange={handleCheckAllPermissionsClick}
              label="All filtered"
              className={s.roleCreateDialog__allPermissions__allFiltered}
            />
            <Tags className={cn(s.roleCreateDialog__allPermissions__list, 'scroll')}>
              {allPermissionsFiltered.map((p) => {
                const isPermissionSelected = !!allPermissionsSelected.find((perm) => perm.id === p.id);

                return (
                  <Tag
                    key={p.id}
                    variant={isPermissionSelected ? 'secondary' : undefined}
                    startAdornment={
                      !isPermissionSelected && (
                        <Checkbox checked={isPermissionSelected} onChange={getHandlerCheckAllPermissionClick(p)} />
                      )
                    }
                  >
                    {p.displayName}
                  </Tag>
                );
              })}
            </Tags>
          </>
        </FormField>
        <FormField label="Selected permissions" className={s.roleCreateDialog__selectedPermissions}>
          <>
            <SearchInput
              placeholder="Search objects"
              value={selectedTextEntered}
              onChange={handleSelectedRoleNameFilter}
            />
            <CheckAll
              allList={allPermissionsSelected}
              selectedValues={selectedPermissionsSelected}
              onChange={handleCheckSelectedPermissionsClick}
              label="All filtered"
              className={s.roleCreateDialog__allPermissions__allFiltered}
            />
            <Tags className={s.roleCreateDialog__selectedPermissions__list}>
              {selectedPermissionsFiltered.map((p) => (
                <Tag
                  key={p.id}
                  startAdornment={
                    <Checkbox
                      checked={!!selectedPermissionsSelected.find((perm) => perm.id === p.id)}
                      onChange={getHandlerCheckSelectedPermissionClick(p)}
                    />
                  }
                  endAdornment={
                    <IconButton
                      //
                      data-id={p.id}
                      icon="g1-remove"
                      variant="secondary"
                      size={20}
                      onClick={getHandlerDeleteSelectedPermissionClick(p)}
                      title="Remove"
                    />
                  }
                >
                  {p.displayName}
                </Tag>
              ))}
            </Tags>
          </>
        </FormField>
      </FormFieldsContainer>
    </Dialog>
  );
};

export default AccessManagerRoleCreateDialog;
