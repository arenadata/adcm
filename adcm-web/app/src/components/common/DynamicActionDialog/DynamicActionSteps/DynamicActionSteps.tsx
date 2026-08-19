import { useMemo, useState, useCallback } from 'react';
import WizardSteps from '@uikit/WizardSteps/WizardSteps';
import { DynamicActionStep } from '../DynamicAction.types';
import DynamicActionConfigSchema from './DynamicActionConfigSchema/DynamicActionConfigSchema';
import DynamicActionAgreeActionHostsGroup from './DynamicActionAgreeActionHostsGroup/DynamicActionAgreeActionHostsGroup';
import DynamicActionHostMapping from './DynamicActionHostMapping/DynamicActionHostMapping';
import type { AdcmActionHostGroup, AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm';
import { getNextStep, isLastStep } from '@uikit/WizardSteps/WizardSteps.utils';
import DynamicActionConfirm from './DynamicActionConfirm/DynamicActionConfirm';
import { getDefaultRunConfig } from '../DynamicActionDialog.utils';
import s from '../DynamicActionDialog.module.scss';
import { useDialogContext } from '@uikit/DialogV2/Dialog.context';

const stepsTitles: Record<DynamicActionStep, string> = {
  [DynamicActionStep.AgreeActionHostsGroup]: 'Hosts group',
  [DynamicActionStep.ConfigSchema]: 'Configuration',
  [DynamicActionStep.HostComponentMapping]: 'Mapping',
  [DynamicActionStep.Confirm]: 'Confirmation',
};

interface DynamicActionsStepsProps {
  clusterId: number | null;
  actionDetails: AdcmDynamicActionDetails;
  actionHostGroup?: AdcmActionHostGroup;
  actionSteps: DynamicActionStep[];
  onSubmit: (runConfig: AdcmDynamicActionRunConfig) => void;
  isConcernControlShown?: boolean;
}

const DynamicActionSteps = ({
  actionDetails,
  actionHostGroup,
  onSubmit,
  clusterId,
  actionSteps,
  isConcernControlShown = true,
}: DynamicActionsStepsProps) => {
  const { onCancel } = useDialogContext();

  const [localActionRunConfig, setLocalActionRunConfig] = useState<AdcmDynamicActionRunConfig>(() =>
    getDefaultRunConfig(),
  );

  const [currentStep, setCurrentStep] = useState<string>(actionSteps[0]);

  const wizardStepsOptions = useMemo(() => {
    return actionSteps.map((step) => ({
      title: stepsTitles[step],
      key: step,
    }));
  }, [actionSteps]);

  const handleStepChange = (data: Partial<AdcmDynamicActionRunConfig>) => {
    const newActionRunConfig = { ...localActionRunConfig, ...data };
    setLocalActionRunConfig(newActionRunConfig);

    if (isLastStep(currentStep, wizardStepsOptions)) {
      onSubmit(newActionRunConfig);
    } else {
      setCurrentStep(getNextStep(currentStep, wizardStepsOptions));
    }
  };

  const handleStateChange = useCallback((data: Partial<AdcmDynamicActionRunConfig>) => {
    setLocalActionRunConfig((prev) => ({ ...prev, ...data }));
  }, []);

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
      {currentStep === DynamicActionStep.AgreeActionHostsGroup && actionHostGroup && (
        <DynamicActionAgreeActionHostsGroup
          actionHostGroup={actionHostGroup}
          onNext={handleStepChange}
          onCancel={onCancel}
        />
      )}
      {currentStep === DynamicActionStep.ConfigSchema && (
        <DynamicActionConfigSchema
          actionDetails={actionDetails}
          onNext={handleStepChange}
          onCancel={onCancel}
          configuration={localActionRunConfig.configuration}
        />
      )}
      {currentStep === DynamicActionStep.HostComponentMapping && clusterId && (
        <DynamicActionHostMapping
          clusterId={clusterId}
          actionDetails={actionDetails}
          onNext={handleStepChange}
          onCancel={onCancel}
        />
      )}
      {currentStep === DynamicActionStep.Confirm && (
        <DynamicActionConfirm
          actionDetails={actionDetails}
          onRun={handleStepChange}
          onCancel={onCancel}
          onStateChange={handleStateChange}
          description={localActionRunConfig.description}
          isVerbose={localActionRunConfig.isVerbose}
          shouldBlockObject={localActionRunConfig.shouldBlockObject}
          isConcernControlShown={isConcernControlShown}
        />
      )}
    </div>
  );
};
export default DynamicActionSteps;
