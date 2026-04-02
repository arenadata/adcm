import Button from '@uikit/Button/Button';
import ButtonGroup from '@uikit/ButtonGroup/ButtonGroup';
import Panel from '@uikit/Panel/Panel';
import s from './ActionWizardSteps.module.scss';
import {
  type AdcmActionProcessOperationStep,
  type AdcmActionProcessStep,
  type AdcmWizardJobsData,
  AdcmWizardStepStates,
  AdcmWizardStepType,
} from '@models/adcm/wizard';
import MarkerIcon from '@uikit/MarkerIcon/MarkerIcon';
import cn from 'classnames';
import ActionWizardConfigurationEditor from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardConfigurationEditor';
import ActionWizardLastStage from '@uikit/ActionWizardSteps/ActionWizardLastStage/ActionWizardLastStage';
import { useActionWizardValidationContext } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardValidationContextProvider/ActionWizardValidationContext.context';
import { useEffect, useState } from 'react';
import type React from 'react';
import type { AdcmDynamicActionDetails, AdcmJob } from '@models/adcm';
import {
  isFirstButtonDisabled,
  isFirstButtonVisible,
  isSecondButtonDisabled,
  isStepFailed,
} from '@uikit/ActionWizardSteps/ActionWizardSteps.utils';
import ActionWizardMapping from '@uikit/ActionWizardSteps/ActionWizardMapping/ActionWizardMapping';

interface ActionWizardStepProps {
  clusterId: number;
  jobsData: AdcmWizardJobsData;
  currentStep: number;
  stageNumber: number;
  steps: AdcmActionProcessStep[];
  isInRunningState: boolean;
  onStepSubmit: (stepType: AdcmWizardStepType) => void;
  onStepChange: () => void;
  onStepReset: (stepId: number) => void;
  entityDynamicActionWizardOperation: React.FC<{
    step: AdcmActionProcessOperationStep;
  }>;
  onClose: () => void;
  selectedStep?: number;
  lastStepActionDetails: AdcmDynamicActionDetails | null;
}

const getStepIcon = (step: AdcmActionProcessStep, hasConflict: boolean, jobsData?: AdcmJob) => {
  if (isStepFailed(step, !hasConflict, jobsData)) {
    return <MarkerIcon variant="round" type="alert" size={12} />;
  }
  if (step.state === AdcmWizardStepStates.Completed) {
    return <MarkerIcon variant="round" type="check" size={12} />;
  }

  return undefined;
};

const stepPanelLabelClassName = (step: AdcmActionProcessStep, hasConflict: boolean, jobsData?: AdcmJob) => {
  return cn(s.actionWizardSteps__stageInfo, {
    [s.actionWizardSteps__stageInfo_running]: step.state === AdcmWizardStepStates.Running,
    [s.actionWizardSteps__stageInfo_error]: isStepFailed(step, !hasConflict, jobsData),
    [s.actionWizardSteps__stageInfo_completed]: step.state === AdcmWizardStepStates.Completed,
  });
};

const getHiddenSteps = (steps: AdcmActionProcessStep[], actualStepId: number) => {
  return steps.reduce<Record<number, boolean>>((acc, step) => {
    acc[step.id] = step.id !== actualStepId;
    return acc;
  }, {});
};

const ActionWizardSteps = ({
  clusterId,
  jobsData,
  selectedStep,
  currentStep,
  stageNumber,
  steps,
  isInRunningState,
  onStepSubmit,
  onStepChange,
  onStepReset,
  entityDynamicActionWizardOperation,
  onClose,
  lastStepActionDetails,
}: ActionWizardStepProps) => {
  const { isValid, isDraft, setIsValid, setIsDraft } = useActionWizardValidationContext();
  const WizardOperation = entityDynamicActionWizardOperation;

  const [hiddenStates, setHiddenStates] = useState(() => getHiddenSteps(steps, selectedStep || currentStep));

  useEffect(() => {
    const element = document.getElementById(`step-${selectedStep}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  }, [steps]);

  useEffect(() => {
    setHiddenStates(getHiddenSteps(steps, selectedStep || currentStep));
  }, [steps, selectedStep, currentStep]);

  useEffect(() => {
    if (selectedStep) {
      handleChangeStepStatus(selectedStep);
    }
  }, [selectedStep]);

  const handleChangeStepStatus = (stepId: number) => {
    setHiddenStates((prev) => ({
      ...prev,
      [stepId]: !prev[stepId],
    }));
  };

  const handleFirstButtonClick = (stepType: AdcmWizardStepType, stepId: number) => {
    if (stepType === AdcmWizardStepType.Operation) {
      onStepSubmit(stepType);
    } else {
      onStepReset(stepId);
      setIsValid(true);
      setIsDraft(false);
    }
  };

  const handleSecondButtonClick = (stepType: AdcmWizardStepType) => {
    if (stepType === AdcmWizardStepType.Operation) {
      onStepChange();
    } else {
      onStepSubmit(stepType);
    }
  };

  return (
    <div className={s.actionWizardSteps__steps}>
      {steps.map((step, stepIndex) => {
        const isStepHidden = hiddenStates[step.id]; // Per-step hidden state
        const isCurrentStep = currentStep === step.id;
        const hasConflict = isCurrentStep && !isValid;

        return (
          <div
            key={step.id}
            id={`step-${step.id}`}
            className={cn(s.actionWizardSteps__step, isStepHidden ? s.actionWizardSteps__step_isHidden : '')}
          >
            <Panel className={s.actionWizardSteps__panel}>
              <div className={stepPanelLabelClassName(step, hasConflict, jobsData[step.id]?.job)}>
                <div className={s.actionWizardSteps__stageNumber}>
                  {stageNumber}.{stepIndex + 1}
                  {getStepIcon(step, hasConflict, jobsData[step.id]?.job)}
                </div>
                <div className={s.actionWizardSteps__labels}>
                  <div className={s.stepLabel} onClick={() => handleChangeStepStatus(step.id)}>
                    {step.displayName}
                  </div>
                  <div className={s.description}>{step.description}</div>
                </div>
              </div>
              <ButtonGroup className={s.actionWizardSteps__buttons}>
                {isFirstButtonVisible(step.type) && (
                  <Button
                    variant="secondary"
                    disabled={isFirstButtonDisabled(step, isCurrentStep, isDraft, isInRunningState)}
                    onClick={() => handleFirstButtonClick(step.type, step.id)}
                  >
                    {step.type === AdcmWizardStepType.Operation ? step?.uiOptions?.buttonName : 'Discard changes'}
                  </Button>
                )}
                <Button
                  onClick={() => handleSecondButtonClick(step.type)}
                  hasError={hasConflict}
                  disabled={hasConflict || step.id !== currentStep || isSecondButtonDisabled(step)}
                >
                  {step.type === AdcmWizardStepType.LastStep ? 'Run' : 'Next step'}
                </Button>
              </ButtonGroup>
            </Panel>
            <div className={s.actionWizardSteps__content}>
              {step.type === AdcmWizardStepType.Configuration && (
                <ActionWizardConfigurationEditor isReadOnly={!isCurrentStep} step={step} />
              )}
              {step.type === AdcmWizardStepType.Operation && <WizardOperation step={step} />}
              {step.type === AdcmWizardStepType.Mapping && (
                <ActionWizardMapping
                  onSetIsValid={setIsValid}
                  clusterId={clusterId}
                  isReadOnly={!isCurrentStep}
                  onClose={onClose}
                  step={step}
                />
              )}
              {step.type === AdcmWizardStepType.LastStep && (
                <ActionWizardLastStage actionDetails={lastStepActionDetails} />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default ActionWizardSteps;
