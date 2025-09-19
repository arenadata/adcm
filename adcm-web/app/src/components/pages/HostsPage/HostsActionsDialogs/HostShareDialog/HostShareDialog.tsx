import { useDispatch } from '@hooks';
import { DialogV2, FormField, FormFieldsContainer, Input, Select } from '@uikit';
import type React from 'react';
import { useEffect } from 'react';
import { useFormHostShareDialog } from './useFormHostShareDialog';
import { closeHostSharingDialog } from '@store/adcm/hosts/hostsActionsSlice';
import s from './HostShareDialog.module.scss';

const HostShareDialog: React.FC = () => {
  const dispatch = useDispatch();

  const {
    formData,
    submit,
    reset,
    onChangeFormData,
    loadRelatedData,
    relatedData: { clustersOptions, host },
    isValid,
    errors,
  } = useFormHostShareDialog();

  const isOpen = !!host;

  useEffect(() => {
    if (isOpen) {
      loadRelatedData();
    } else {
      reset();
    }
  }, [isOpen]);

  if (!host) return null;

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ name: event.target.value });
  };
  const handleClusterNameChange = (value: number | null) => {
    onChangeFormData({ clusterId: value });
  };

  const handleCloseDialog = () => {
    dispatch(closeHostSharingDialog());
  };

  return (
    <DialogV2
      title="Create subhost"
      onAction={submit}
      onCancel={handleCloseDialog}
      isActionDisabled={!isValid}
      actionButtonLabel="Create"
      className={s.hostShareDialog}
    >
      <FormFieldsContainer>
        <div className={s.hostShareDialog__readOnlyFields}>
          <FormField label="Host">
            <Input value={host.name} type="text" readOnly variant="secondary" />
          </FormField>
          <FormField label="Hostprovider">
            <Input value={host.hostprovider.name} readOnly variant="secondary" />
          </FormField>
        </div>

        <FormField label="Name" error={errors.name}>
          <Input value={formData.name} type="text" onChange={handleNameChange} placeholder="Enter subhost name" />
        </FormField>
        <FormField label="Cluster">
          <Select
            placeholder="Select cluster"
            value={formData.clusterId}
            onChange={handleClusterNameChange}
            options={clustersOptions}
          />
        </FormField>
      </FormFieldsContainer>
    </DialogV2>
  );
};

export default HostShareDialog;
