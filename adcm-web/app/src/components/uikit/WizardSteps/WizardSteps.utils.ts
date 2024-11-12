import type { WizardStep } from '@uikit/WizardSteps/WizardSteps.types';

export const isLastStep = (stepKey: WizardStep['key'], steps: WizardStep[]) => {
  return steps.at(-1)?.key === stepKey;
};

export const isFirstStep = (stepKey: WizardStep['key'], steps: WizardStep[]) => {
  return steps[0]?.key === stepKey;
};

export const getStepIndex = (stepKey: WizardStep['key'], steps: WizardStep[]) => {
  return steps.findIndex(({ key }) => key === stepKey);
};

export const getNextStep = (currentStepKey: WizardStep['key'], steps: WizardStep[]) => {
  const currentStepIndex = getStepIndex(currentStepKey, steps);

  return steps[currentStepIndex + 1].key;
};

export const getPrevStep = (currentStepKey: WizardStep['key'], steps: WizardStep[]) => {
  const currentStepIndex = getStepIndex(currentStepKey, steps);

  return steps[currentStepIndex - 1].key;
};
