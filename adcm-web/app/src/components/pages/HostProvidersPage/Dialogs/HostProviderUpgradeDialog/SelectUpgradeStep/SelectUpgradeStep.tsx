import React, { useMemo } from 'react';
import { FormField, FormFieldsContainer, Select } from '@uikit';
import TextFormField from '@commonComponents/Forms/TextFormField/TextFormField';
import { useStore } from '@hooks';
import type { UpgradeStepFormProps } from '../HostProviderUpgradeDialog.types';

const SelectUpgradeStep: React.FC<UpgradeStepFormProps> = ({ formData, onChange }) => {
  const hostProvider = useStore(({ adcm }) => adcm.hostProviderUpgrades.dialog.hostProvider);
  const upgradesList = useStore(({ adcm }) => adcm.hostProviderUpgrades.relatedData.upgradesList);

  const handleChange = (upgradeId: number | null) => {
    onChange({ upgradeId });
  };

  const upgradesOptions = useMemo(() => {
    return upgradesList.map((upgrade) => ({
      label: upgrade.name,
      value: upgrade.id,
    }));
  }, [upgradesList]);

  return (
    <FormFieldsContainer>
      <FormField label="Hostprovider">
        <TextFormField>{hostProvider?.name}</TextFormField>
      </FormField>
      <FormField label="Upgrade to version">
        <Select
          placeholder="Select available"
          value={formData.upgradeId}
          onChange={handleChange}
          options={upgradesOptions}
        />
      </FormField>
    </FormFieldsContainer>
  );
};
export default SelectUpgradeStep;
