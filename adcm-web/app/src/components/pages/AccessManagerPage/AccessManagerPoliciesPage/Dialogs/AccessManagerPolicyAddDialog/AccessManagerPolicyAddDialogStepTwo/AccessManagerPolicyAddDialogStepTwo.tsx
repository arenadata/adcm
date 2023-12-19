import React, { useMemo } from 'react';
import { FormField, FormFieldsContainer, Select } from '@uikit';
import { useAccessManagerPolicyAddDialogStepTwo } from './useAccessManagerPolicyAddDialogStepTwo';
import MultiSelect from '@uikit/Select/MultiSelect/MultiSelect';
import { AccessManagerPolicyAddDialogFormData, ChangeFormDataPayload } from '../AccessManagerPolicyAddDialog.types';

interface AccessManagerPolicyAddDialogStepTwoProps {
  formData: AccessManagerPolicyAddDialogFormData;
  changeFormData: (value: ChangeFormDataPayload) => void;
}

const AccessManagerPolicyAddDialogStepTwo: React.FC<AccessManagerPolicyAddDialogStepTwoProps> = ({
  formData,
  changeFormData,
}) => {
  const stepTypes = formData.objectTypes;
  const {
    relatedData: { clusterOptions, serviceOptions, hostproviderOptions, hostOptions, serviceClusters },
  } = useAccessManagerPolicyAddDialogStepTwo();

  const serviceClustersOptions = useMemo(() => {
    const clusters = serviceClusters
      .filter((service) => service.name === formData.serviceName)
      .flatMap((service) => service.clusters);

    return clusters?.map(({ id, name }) => ({
      value: id,
      label: name,
    }));
  }, [formData.serviceName, serviceClusters]);

  const handleServiceChange = (value: string | null) => {
    changeFormData({ serviceName: value, serviceClusterIds: [] });
  };

  const handleServiceClusterChange = (value: number[]) => {
    changeFormData({ serviceClusterIds: value });
  };

  const handleClusterChange = (value: number[]) => {
    changeFormData({ clusterIds: value });
  };

  const handleHostChange = (value: number[]) => {
    changeFormData({ hostIds: value });
  };

  const handleHostproviderChange = (value: number[]) => {
    changeFormData({ hostproviderIds: value });
  };

  return (
    <>
      <FormFieldsContainer>
        {stepTypes.map((step) => (
          <React.Fragment key={step}>
            {step === 'cluster' && (
              <FormField label="Cluster">
                <MultiSelect
                  checkAllLabel="All clusters"
                  placeholder="Select cluster"
                  disabled={formData.clusterIds.length === 0 && formData.serviceName !== ''}
                  value={formData.clusterIds}
                  onChange={handleClusterChange}
                  options={clusterOptions}
                />
              </FormField>
            )}
            {step === 'service' && (
              <>
                <FormField label="Service">
                  <Select
                    placeholder="Select service"
                    disabled={formData.clusterIds.length > 0 && formData.serviceName === ''}
                    value={formData.serviceName}
                    onChange={handleServiceChange}
                    options={serviceOptions}
                    maxHeight={200}
                  />
                </FormField>
                <FormField label="Parent">
                  <MultiSelect
                    disabled={formData.serviceName.length === 0}
                    checkAllLabel="All clusters"
                    placeholder="Select cluster"
                    value={formData.serviceClusterIds}
                    onChange={handleServiceClusterChange}
                    options={serviceClustersOptions}
                  />
                </FormField>
              </>
            )}
            {step === 'host' && (
              <FormField label="Host">
                <MultiSelect
                  checkAllLabel="All hosts"
                  placeholder="Select host"
                  disabled={formData.hostproviderIds.length > 0}
                  value={formData.hostIds}
                  onChange={handleHostChange}
                  options={hostOptions}
                />
              </FormField>
            )}
            {step === 'provider' && (
              <FormField label="Provider">
                <MultiSelect
                  checkAllLabel="All Providers"
                  placeholder="Select provider"
                  disabled={formData.hostIds.length > 0}
                  value={formData.hostproviderIds}
                  onChange={handleHostproviderChange}
                  options={hostproviderOptions}
                />
              </FormField>
            )}
          </React.Fragment>
        ))}
      </FormFieldsContainer>
      {stepTypes.length === 0 && (
        <div>The selected role does not require specifying an object. The policy will apply to all ADCM objects.</div>
      )}
    </>
  );
};
export default AccessManagerPolicyAddDialogStepTwo;
