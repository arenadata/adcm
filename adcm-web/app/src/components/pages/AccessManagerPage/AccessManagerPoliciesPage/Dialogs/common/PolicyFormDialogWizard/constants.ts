import type { WizardStep } from '@uikit/WizardSteps/WizardSteps.types';

export enum Steps {
  MainInfo = 'mainInfo',
  Object = 'object',
}

export const steps = [
  {
    title: 'Main info',
    key: Steps.MainInfo,
  },
  {
    title: 'Object',
    key: Steps.Object,
  },
] as WizardStep[];
