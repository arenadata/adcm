import React from 'react';
import s from './ActionWizardMapItem.module.scss';
import type { AdcmActionProcessStep, AdcmActionWizardProcess, AdcmWizardStage } from '@models/adcm/wizard';
import MarkerIcon from '@uikit/MarkerIcon/MarkerIcon';
import cn from 'classnames';
import { useDispatch, useStore } from '@hooks';
import { setSelectedStepId } from '@store/adcm/clusters/clustersWizardActionsSlice';
import { useActionWizardValidationContext } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardValidationContextProvider/ActionWizardValidationContext.context';

interface MapItemStagesProps {
  process: AdcmActionWizardProcess;
}

const isStepFailed = (step: AdcmActionProcessStep, currentStep: number, isValid: boolean): boolean => {
  return (step.id <= currentStep && !isValid) || step.state === 'broken';
};

const getStepIcon = (step: AdcmActionProcessStep, currentStep: number, isValid: boolean) => {
  if (isStepFailed(step, currentStep, isValid)) {
    return <MarkerIcon variant="round" type="alert" size={12} />;
  }
  if (step.state === 'completed') {
    return <MarkerIcon variant="round" type="check" size={12} />;
  }

  return undefined;
};

const getStageIcon = (stage: AdcmWizardStage, currentStep: number, isValid: boolean) => {
  if (stage.steps.some((step) => isStepFailed(step, currentStep, isValid))) {
    return <MarkerIcon variant="round" type="alert" size={12} />;
  }
  if (stage.steps.every((step) => step.state === 'completed')) {
    return <MarkerIcon variant="round" type="check" size={12} />;
  }

  return undefined;
};

const stageClassName = (stage: AdcmWizardStage, currentStep: number, isValid: boolean) => {
  return cn(s.mapItem__stage, {
    [s.mapItem__stage_disabled]: stage.steps.every((step) => step.state === 'created' && step.id !== currentStep),
    [s.mapItem__stage_error]: stage.steps.some((step) => isStepFailed(step, currentStep, isValid)),
    [s.mapItem__stage_running]: stage.steps.some((step) => step.state === 'running'),
    [s.mapItem__stage_completed]: stage.steps.every((step) => step.state === 'completed'),
    [s.active]: stage.steps.some((step) => step.id === currentStep),
  });
};

const stepClassName = (step: AdcmActionProcessStep, currentStep: number, isValid: boolean) => {
  return cn(s.mapItem__step, {
    [s.mapItem__step_disabled]: step.state === 'created' && step.id !== currentStep,
    [s.mapItem__step_error]: isStepFailed(step, currentStep, isValid),
    [s.mapItem__step_running]: step.state === 'running',
    [s.mapItem__step_completed]: step.state === 'completed',
  });
};

const MapItemStages: React.FC<MapItemStagesProps> = ({ process }: MapItemStagesProps) => {
  const dispatch = useDispatch();
  const selectedStep = useStore((s) => s.adcm.clustersWizardActions.selectedStepId);

  const { isValid } = useActionWizardValidationContext();
  const currentStep = selectedStep ?? process?.currentStep;

  const handleSwitchStage = (stage: AdcmWizardStage, currentStep: number) => {
    const hasCurrentStep = stage.steps.some((step) => step.id === currentStep);
    const isDisabled = stage.steps.every((step) => step.state === 'created');

    if (hasCurrentStep || isDisabled) {
      return null;
    }

    dispatch(setSelectedStepId(stage.steps[0]?.id));
  };

  return (
    <div key={process.stages.length} className={s.mapItem__stages}>
      {process.stages.map((stage, index) => (
        <React.Fragment key={stage.displayName}>
          <div
            className={stageClassName(stage, process?.currentStep, isValid)}
            onClick={() => handleSwitchStage(stage, currentStep)}
          >
            <div className={s.mapItem__index}>
              {index + 1}
              {getStageIcon(stage, currentStep, isValid)}
            </div>

            <div className={s.mapItem__title}>{stage.displayName}</div>
          </div>
          {stage.steps && stage.steps.length > 1 && (
            <MapItemSteps steps={stage.steps} stageIndex={index + 1} process={process} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
};

export default MapItemStages;

interface ActionWizardStepListProps {
  steps: AdcmActionProcessStep[];
  stageIndex: number;
  process: AdcmActionWizardProcess;
}

const MapItemSteps: React.FC<ActionWizardStepListProps> = ({ steps, stageIndex, process }) => {
  const dispatch = useDispatch();
  const selectedStep = useStore((s) => s.adcm.clustersWizardActions.selectedStepId);

  const { isValid } = useActionWizardValidationContext();

  const handleSwitchStep = (step: AdcmActionProcessStep) => {
    if (step.id === selectedStep) return null;
    dispatch(setSelectedStepId(step.id));
  };

  return (
    <div key={stageIndex} className={s.mapItem__steps}>
      {steps.map((step, stepIndex) => (
        <div
          key={step.id}
          className={stepClassName(step, process?.currentStep, isValid)}
          onClick={() => handleSwitchStep(step)}
        >
          <div className={s.mapItem__index}>
            {`${stageIndex}.${stepIndex + 1}`}
            {getStepIcon(step, process?.currentStep, isValid)}
          </div>
          <div className={s.mapItem__title}>{step.displayName}</div>
        </div>
      ))}
    </div>
  );
};
