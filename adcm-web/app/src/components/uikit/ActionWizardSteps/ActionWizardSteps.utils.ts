import {
  type AdcmActionProcessStep,
  type AdcmWizardStage,
  AdcmWizardStepStates,
  AdcmWizardStepType,
} from '@models/adcm/wizard';
import { type AdcmJob, AdcmJobStatus } from '@models/adcm';

const wizardStepStates = new Set([AdcmWizardStepStates.Running, AdcmWizardStepStates.Completed]);

const wizardStepType = new Set([
  AdcmWizardStepType.Operation,
  AdcmWizardStepType.Configuration,
  AdcmWizardStepType.Mapping,
]);

export const isStepFailed = (step: AdcmActionProcessStep, isValid: boolean, jobsData?: AdcmJob): boolean => {
  return !isValid || jobsData?.status === AdcmJobStatus.Failed || step.state === AdcmWizardStepStates.Broken;
};

export const lastStepId = (stages: AdcmWizardStage[]) => {
  return stages.flatMap((stage) => stage.steps).find((step) => step.type === AdcmWizardStepType.LastStep)?.id || null;
};

export const checkForBrokenStep = (stages: AdcmWizardStage[]) => {
  return stages.flatMap((stage) => stage.steps).find((step) => step.state === 'broken')?.id ?? undefined;
};

export const getCurrentStageNotDisabledStepIds = (
  currentStep: number,
  currentStepFromEndpoint: number,
  stages: AdcmWizardStage[],
): number[] => {
  const currentStage = stages.find((stage) =>
    stage.steps.some((step) => step.id === currentStep && step.type !== AdcmWizardStepType.LastStep),
  );

  if (!currentStage) {
    return [];
  }

  if (currentStage.steps.every((step) => step.state === AdcmWizardStepStates.Completed)) {
    return currentStage.steps.map((step) => step.id);
  }

  return currentStage.steps.filter((step) => step.id <= currentStepFromEndpoint).map((step) => step.id);
};

export const getMaxStepId = (steps: AdcmActionProcessStep[]) => {
  return steps.length > 0 ? Math.max(...steps.map((step) => step.id)) : -1;
};

export const isFirstButtonDisabled = (
  step: AdcmActionProcessStep,
  isCurrentStep: boolean,
  isDraft: boolean,
  isInRunningState: boolean,
) => {
  if ([AdcmWizardStepType.Configuration, AdcmWizardStepType.Mapping].includes(step.type)) {
    return (isCurrentStep && !isDraft) || isInRunningState;
  }

  if (step.type === AdcmWizardStepType.Operation && step.state === AdcmWizardStepStates.Skipped) {
    return true;
  }

  return wizardStepStates.has(step.state);
};

export const isSecondButtonDisabled = (step: AdcmActionProcessStep) => {
  if (step.type === AdcmWizardStepType.Operation) {
    return step.required && step.state !== AdcmWizardStepStates.Completed;
  }

  return step.state === AdcmWizardStepStates.Completed;
};

export const isFirstButtonVisible = (stepType: AdcmWizardStepType) => {
  return wizardStepType.has(stepType);
};
