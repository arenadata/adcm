import React, { useMemo, useState } from 'react';
import WizardSteps from '@uikit/WizardSteps/WizardSteps';
import DynamicActionConfigSchema from '@commonComponents/DynamicActionDialog/DynamicActionConfigSchema/DynamicActionConfigSchema';
import {
  DynamicActionCommonOptions,
  DynamicActionType,
} from '@commonComponents/DynamicActionDialog/DynamicAction.types';
import DynamicActionHostMapping from '@commonComponents/DynamicActionDialog/DynamicActionHostMapping/DynamicActionHostMapping';
import { AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import s from '../DynamicActionDialog.module.scss';
import { getNextStep, isLastStep } from '@uikit/WizardSteps/WizardSteps.utils';

const stepsTitles: Record<DynamicActionType, string> = {
  [DynamicActionType.ConfigSchema]: 'Configuration',
  [DynamicActionType.HostComponentMapping]: 'Host - Component',
  [DynamicActionType.Confirm]: 'Confirm',
};

interface DynamicActionsStepsProps extends DynamicActionCommonOptions {
  clusterId: number | null;
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

  const wizardStepsOptions = useMemo(() => {
    return actionSteps.map((step) => ({
      title: stepsTitles[step],
      key: step,
    }));
  }, [actionSteps]);

  const handleSubmit = (data: Partial<AdcmDynamicActionRunConfig>) => {
    const newActionRunConfig = { ...localActionRunConfig, ...data };
    setLocalActionRunConfig(newActionRunConfig);

    if (isLastStep(currentStep, wizardStepsOptions)) {
      // if submit of last step - call full submit
      onSubmit(newActionRunConfig);
    } else {
      setCurrentStep(getNextStep(currentStep, wizardStepsOptions));
    }
  };

  const isFewSteps = actionSteps.length > 1;

  return (
    <div>
      {isFewSteps && (
        <WizardSteps
          steps={wizardStepsOptions}
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
          submitLabel={isFewSteps ? 'Next' : 'Run'}
        />
      )}
      {currentStep === DynamicActionType.HostComponentMapping && clusterId && (
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
