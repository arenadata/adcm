import React, { useState } from 'react';
import WizardSteps from '@uikit/WizardSteps/WizardSteps';
import { WizardStep } from '@uikit/WizardSteps/WizardSteps.types';
import DynamicActionConfigSchema from '@commonComponents/DynamicActionDialog/DynamicActionConfigSchema/DynamicActionConfigSchema';
import {
  DynamicActionCommonOptions,
  DynamicActionType,
} from '@commonComponents/DynamicActionDialog/DynamicAction.types';
import DynamicActionHostMapping from '@commonComponents/DynamicActionDialog/DynamicActionHostMapping/DynamicActionHostMapping';
import { AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import s from '../DynamicActionDialog.module.scss';
import { getNextStep, isLastStep } from '@uikit/WizardSteps/WizardSteps.utils';

const steps = [
  {
    title: 'Configuration',
    key: DynamicActionType.ConfigSchema as string,
  },
  {
    title: 'Host - Component',
    key: DynamicActionType.HostComponentMapping as string,
  },
] as WizardStep[];

interface DynamicActionsStepsProps extends DynamicActionCommonOptions {
  clusterId: number;
  actionSteps: DynamicActionType[];
}

const DynamicActionSteps: React.FC<DynamicActionsStepsProps> = ({
  actionDetails,
  onSubmit,
  onCancel,
  clusterId,
  actionSteps,
}) => {
  const [localActionRunConfig, setLocalActionRunConfig] = useState<Partial<AdcmDynamicActionRunConfig>>(() => {
    return { config: {}, hostComponentMap: [] };
  });

  const [currentStep, setCurrentStep] = useState<string>(actionSteps[0]);

  const handleSubmit = (data: Partial<AdcmDynamicActionRunConfig>) => {
    const newActionRunConfig = { ...localActionRunConfig, ...data };
    setLocalActionRunConfig(newActionRunConfig);

    if (isLastStep(currentStep, steps)) {
      // if submit of last step - call full submit
      onSubmit(newActionRunConfig);
    } else {
      setCurrentStep(getNextStep(currentStep, steps));
    }
  };

  return (
    <div>
      {actionSteps.length > 1 && (
        <WizardSteps
          steps={steps}
          currentStep={currentStep}
          onChangeStep={setCurrentStep}
          className={s.dynamicActionDialog__tabs}
        />
      )}
      {currentStep === DynamicActionType.ConfigSchema && (
        <DynamicActionConfigSchema
          actionDetails={actionDetails}
          onSubmit={handleSubmit}
          onCancel={onCancel}
          submitLabel="Next"
        />
      )}
      {currentStep === DynamicActionType.HostComponentMapping && (
        <DynamicActionHostMapping
          clusterId={clusterId}
          actionDetails={actionDetails}
          onSubmit={handleSubmit}
          onCancel={onCancel}
        />
      )}
    </div>
  );
};
export default DynamicActionSteps;
