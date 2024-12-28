import type React from 'react';
import { useMemo } from 'react';
import { FormField, FormFieldsContainer, Select } from '@uikit';
import TextFormField from '@commonComponents/Forms/TextFormField/TextFormField';
import { useStore } from '@hooks';
import type { UpgradeStepFormProps } from '@pages/ClustersPage/Dialogs/UpgradeClusterDialog/UpgradeClusterDialog.types';

const SelectUpgradeStep: React.FC<UpgradeStepFormProps> = ({ formData, onChange }) => {
  const cluster = useStore(({ adcm }) => adcm.clusterUpgrades.dialog.cluster);
  const upgradesList = useStore(({ adcm }) => adcm.clusterUpgrades.relatedData.upgradesList);

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
      <FormField label="Cluster">
        <TextFormField>{cluster?.name}</TextFormField>
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
