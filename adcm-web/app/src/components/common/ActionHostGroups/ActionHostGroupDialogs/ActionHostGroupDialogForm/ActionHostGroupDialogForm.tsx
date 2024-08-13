import React, { useMemo } from 'react';
import type { FormErrors } from '@hooks/useForm';
import { FormField, FormFieldsContainer, Input } from '@uikit';
import { AdcmActionHostGroupHost } from '@models/adcm';
import type { AdcmActionHostGroupFormData } from './useActionHostGroupDialogForm';
import ListTransfer from '@uikit/ListTransfer/ListTransfer';
import { availableHostsPanel, selectedHostsPanel } from './ActionHostGroupDialogForm.constants';
import s from './ActionHostGroupDialogForm.module.scss';

export interface ActionHostGroupDialogFormProps {
  formData: AdcmActionHostGroupFormData;
  hostCandidates: AdcmActionHostGroupHost[];
  errors: FormErrors<AdcmActionHostGroupFormData>;
  onChangeFormData: (changes: Partial<AdcmActionHostGroupFormData>) => void;
}

const ActionHostGroupDialogForm = ({
  formData,
  hostCandidates,
  errors,
  onChangeFormData,
}: ActionHostGroupDialogFormProps) => {
  const allHosts = useMemo(() => {
    return hostCandidates.map((host) => {
      return {
        key: host.id,
        label: host.name,
      };
    });
  }, [hostCandidates]);

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ name: event.target.value });
  };

  const handleDescriptionChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ description: event.target.value });
  };

  const handleHostsChange = (hostIds: Set<number>) => {
    onChangeFormData({ hosts: hostIds });
  };

  return (
    <FormFieldsContainer className={s.actionHostGroupDialogForm}>
      <div className={s.actionHostGroupDialogForm__column}>
        <FormField label="Action hosts group name" error={errors.name}>
          <Input
            value={formData.name}
            type="text"
            onChange={handleNameChange}
            placeholder="Enter name"
            autoComplete="off"
            autoFocus
          />
        </FormField>
        <FormField label="Description">
          <Input
            value={formData.description}
            type="text"
            onChange={handleDescriptionChange}
            placeholder="Enter short description"
            autoComplete="off"
          />
        </FormField>
      </div>

      <ListTransfer
        srcList={allHosts}
        destKeys={formData.hosts}
        srcOptions={availableHostsPanel}
        destOptions={selectedHostsPanel}
        destError={errors.hosts}
        className={s.roleDialogForm__listTransfer}
        onChangeDest={handleHostsChange}
      />
    </FormFieldsContainer>
  );
};

export default ActionHostGroupDialogForm;
