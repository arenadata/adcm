import React from 'react';
import s from './ActionWizardMapItem.module.scss';
import {
  type AdcmActionProcessStep,
  type AdcmActionWizardProcess,
  type AdcmWizardJobsData,
  type AdcmWizardStage,
  AdcmWizardStepStates,
} from '@models/adcm/wizard';
import { AdcmWizardStepType } from '@models/adcm/wizard';
import MarkerIcon from '@uikit/MarkerIcon/MarkerIcon';
import cn from 'classnames';
import { useDispatch, useStore } from '@hooks';
import { setSelectedStepId } from '@store/adcm/clusters/clustersWizardActionsSlice';
import { useActionWizardValidationContext } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardValidationContextProvider/ActionWizardValidationContext.context';
import type { AdcmJob } from '@models/adcm';
import { setBrokenStepError } from '@store/adcm/clusters/clustersWizardSlice';
import { isStepFailed } from '@uikit/ActionWizardSteps/ActionWizardSteps.utils';

interface MapItemStagesProps {
  process: AdcmActionWizardProcess;
}

const isStageActiveWithError = (
  stage: AdcmWizardStage,
  currentStep: number,
  isValid: boolean,
  jobsData: AdcmWizardJobsData,
): boolean => {
  const stepsWithinStage = new Set(stage.steps.map((step) => step.id));
  return (
    stepsWithinStage.has(currentStep) && stage.steps.some((step) => isStepFailed(step, isValid, jobsData[step.id]?.job))
  );
};

const getStepIcon = (step: AdcmActionProcessStep, isValid: boolean, jobsData?: AdcmJob) => {
  if (isStepFailed(step, isValid, jobsData)) {
    return <MarkerIcon variant="round" type="alert" size={12} />;
  }
  if (step.state === AdcmWizardStepStates.Completed) {
    return <MarkerIcon variant="round" type="check" size={12} />;
  }

  return undefined;
};

const getStageIcon = (stage: AdcmWizardStage, currentStep: number, isValid: boolean, jobsData: AdcmWizardJobsData) => {
  if (isStageActiveWithError(stage, currentStep, isValid, jobsData)) {
    return <MarkerIcon variant="round" type="alert" size={12} />;
  }
  if (stage.steps.every((step) => step.state === AdcmWizardStepStates.Completed)) {
    return <MarkerIcon variant="round" type="check" size={12} />;
  }

  return undefined;
};

const stageClassName = (
  stage: AdcmWizardStage,
  currentStep: number,
  isValid: boolean,
  jobsData: AdcmWizardJobsData,
) => {
  return cn(s.mapItem__stage, {
    [s.mapItem__stage_disabled]: stage.steps.every(
      (step) => step.state === AdcmWizardStepStates.Created && step.id > currentStep,
    ),
    [s.mapItem__stage_error]: isStageActiveWithError(stage, currentStep, isValid, jobsData),
    [s.mapItem__stage_running]: stage.steps.some((step) => step.state === AdcmWizardStepStates.Running),
    [s.mapItem__stage_completed]: stage.steps.every((step) => step.state === AdcmWizardStepStates.Completed),
    [s.active]: stage.steps.some((step) => step.id === currentStep),
  });
};

const stepClassName = (step: AdcmActionProcessStep, currentStep: number, isValid: boolean, jobsData?: AdcmJob) => {
  return cn(s.mapItem__step, {
    [s.mapItem__step_disabled]: step.state === AdcmWizardStepStates.Created && step.id > currentStep,
    [s.mapItem__step_error]: isStepFailed(step, isValid, jobsData),
    [s.mapItem__step_running]: step.state === AdcmWizardStepStates.Running,
    [s.mapItem__step_completed]: step.state === AdcmWizardStepStates.Completed,
  });
};

const MapItemStages: React.FC<MapItemStagesProps> = ({ process }: MapItemStagesProps) => {
  const dispatch = useDispatch();
  const selectedStep = useStore((s) => s.adcm.clustersWizardActions.selectedStepId);
  const jobsData = useStore((s) => s.adcm.clustersWizard.jobsData);

  const { isValid } = useActionWizardValidationContext();
  const currentStep = selectedStep ?? process?.currentStep;

  const handleSwitchStage = (stage: AdcmWizardStage, currentStep: number) => {
    const hasCurrentStep = stage.steps.some((step) => step.id === currentStep);
    const isDisabled = stage.steps.every((step) => step.state === AdcmWizardStepStates.Created);

    if (hasCurrentStep || isDisabled) {
      return null;
    }

    dispatch(setBrokenStepError(undefined));
    dispatch(setSelectedStepId(stage.steps[0]?.id));
  };

  return (
    <div key={process.stages.length} className={s.mapItem__stages}>
      {process.stages.map((stage, index) => (
        <React.Fragment key={stage.displayName}>
          <div
            className={stageClassName(stage, process?.currentStep, isValid, jobsData)}
            onClick={() => handleSwitchStage(stage, currentStep)}
          >
            <div className={s.mapItem__index}>
              {index + 1}
              {getStageIcon(stage, currentStep, isValid, jobsData)}
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
  const jobsData = useStore((s) => s.adcm.clustersWizard.jobsData);

  const { isValid } = useActionWizardValidationContext();

  const handleSwitchStep = (step: AdcmActionProcessStep) => {
    if (step.id === selectedStep) return null;
    dispatch(setBrokenStepError(undefined));
    dispatch(setSelectedStepId(step.id));
  };

  return (
    <div key={stageIndex} className={s.mapItem__steps}>
      {steps.map((step, stepIndex) => {
        const isCurrentStep = process?.currentStep === step.id;
        const hasConflict = isCurrentStep && !isValid;
        const isStepValid = step.type === AdcmWizardStepType.Configuration ? !hasConflict : true;
        const stepClasses = stepClassName(step, process?.currentStep, isStepValid, jobsData[step.id]?.job);
        const stepNumber = `${stageIndex}.${stepIndex + 1}`;

        return (
          <div key={step.id} className={stepClasses} onClick={() => handleSwitchStep(step)}>
            <div className={s.mapItem__index}>
              {stepNumber}
              {getStepIcon(step, isStepValid, jobsData[step.id]?.job)}
            </div>
            <div className={s.mapItem__title}>{step.displayName}</div>
          </div>
        );
      })}
    </div>
  );
};
